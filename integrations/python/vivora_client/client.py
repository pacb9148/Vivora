"""Vivora API client. REST uses only the stdlib; chat() needs `websockets`."""
from __future__ import annotations

import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

CONFIG_PATH = Path(os.environ.get("VIVORA_CONFIG", Path.home() / ".vivora" / "config.json"))
DEFAULT_URL = "http://localhost:8000"


class VivoraError(RuntimeError):
    pass


def load_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        pass
    if os.environ.get("VIVORA_URL"):
        cfg["url"] = os.environ["VIVORA_URL"]
    if os.environ.get("VIVORA_TOKEN"):
        cfg["token"] = os.environ["VIVORA_TOKEN"]
    cfg.setdefault("url", DEFAULT_URL)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass


class Vivora:
    def __init__(self, url: Optional[str] = None, token: Optional[str] = None):
        cfg = load_config()
        self.url = (url or cfg["url"]).rstrip("/")
        self.token = token or cfg.get("token")

    # -- transport ---------------------------------------------------------
    def _req(self, method: str, path: str, *, json_body=None, form=None, files=None, auth=True):
        headers = {}
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        elif files is not None:
            boundary = uuid.uuid4().hex
            parts = []
            for k, v in (form or {}).items():
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for k, p in files.items():
                p = Path(p)
                ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{p.name}"\r\n'
                    f"Content-Type: {ctype}\r\n\r\n".encode() + p.read_bytes() + b"\r\n"
                )
            parts.append(f"--{boundary}--\r\n".encode())
            data = b"".join(parts)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body = r.read()
        except urllib.error.HTTPError as e:
            raise VivoraError(f"{method} {path} -> {e.code}: {e.read().decode(errors='replace')}") from None
        except urllib.error.URLError as e:
            raise VivoraError(f"Cannot reach Vivora at {self.url} ({e.reason}). Is the service running? (vivora up)") from None
        return json.loads(body) if body else None

    # -- auth --------------------------------------------------------------
    def health(self):
        return self._req("GET", "/health", auth=False)

    def register(self, email: str, username: str, password: str):
        return self._req("POST", "/api/v1/users/register", json_body={"email": email, "username": username, "password": password}, auth=False)

    def login(self, email: str, password: str, save: bool = True) -> str:
        r = self._req("POST", "/api/v1/users/login", form={"username": email, "password": password}, auth=False)
        self.token = r["access_token"]
        if save:
            cfg = load_config()
            cfg.update(url=self.url, token=self.token)
            save_config(cfg)
        return self.token

    def me(self):
        return self._req("GET", "/api/v1/users/me")

    # -- resources ---------------------------------------------------------
    def upload_avatar(self, file: str, name: str):
        return self._req("POST", "/api/v1/avatars/upload", form={"name": name}, files={"file": file})

    def avatars(self):
        return self._req("GET", "/api/v1/avatars/")

    def avatar(self, avatar_id: str):
        return self._req("GET", f"/api/v1/avatars/{avatar_id}")

    def delete_avatar(self, avatar_id: str):
        return self._req("DELETE", f"/api/v1/avatars/{avatar_id}")

    def clone_voice(self, audio: str, name: str, language: str = "en"):
        return self._req("POST", "/api/v1/voices/clone", form={"name": name, "language": language}, files={"audio": audio})

    def voices(self):
        return self._req("GET", "/api/v1/voices/")

    def set_avatar_voice(self, avatar_id: str, voice_id: str):
        return self._req("PUT", f"/api/v1/avatars/{avatar_id}/voice?voice_id={urllib.parse.quote(voice_id)}")

    def create_session(self, avatar_id: str, settings: Optional[dict] = None):
        return self._req("POST", "/api/v1/sessions/create", json_body={"avatar_id": avatar_id, "settings": settings})

    def end_session(self, session_id: str):
        return self._req("POST", f"/api/v1/sessions/{session_id}/end")

    def messages(self, session_id: str):
        return self._req("GET", f"/api/v1/messages/session/{session_id}")

    # -- realtime chat -----------------------------------------------------
    def chat(self, session_id: str, text: str, language: Optional[str] = None, voice_id: Optional[str] = None) -> Iterator[dict]:
        """Send one text turn; yield server events until the reply (and its video) finishes."""
        try:
            import websockets
        except ImportError:
            raise VivoraError("chat() needs websockets: pip install 'vivora-client[chat]'") from None
        ws_url = self.url.replace("http", "ws", 1) + f"/ws/session/{session_id}?token={urllib.parse.quote(self.token or '')}"

        async def run(queue):
            async with websockets.connect(ws_url, max_size=None) as ws:
                if language:
                    await ws.send(json.dumps({"type": "set_language", "language": language}))
                if voice_id:
                    await ws.send(json.dumps({"type": "set_voice", "voice_id": voice_id}))
                await ws.send(json.dumps({"type": "text", "text": text}))
                async for raw in ws:
                    ev = json.loads(raw)
                    queue.append(ev)
                    if ev.get("type") in ("video_chunk_end", "error"):
                        break

        import asyncio
        events: list = []
        asyncio.run(asyncio.wait_for(run(events), timeout=600))
        yield from events
