"""Minimal stdio MCP server (stdlib only) so ANY MCP-capable agent/model can drive Vivora."""
import json
import sys

from .client import Vivora, VivoraError

TOOLS = {
    "vivora_status": ("Check the Vivora service is up.", {}, lambda v, a: v.health()),
    "vivora_list_avatars": ("List avatars.", {}, lambda v, a: v.avatars()),
    "vivora_upload_avatar": ("Create an avatar from a local photo/video path.", {"file": "string", "name": "string"}, lambda v, a: v.upload_avatar(a["file"], a["name"])),
    "vivora_clone_voice": ("Clone a voice from a local audio file.", {"audio": "string", "name": "string", "language": "string?"}, lambda v, a: v.clone_voice(a["audio"], a["name"], a.get("language", "en"))),
    "vivora_list_voices": ("List cloned voices.", {}, lambda v, a: v.voices()),
    "vivora_create_session": ("Start a conversation session with an avatar.", {"avatar_id": "string"}, lambda v, a: v.create_session(a["avatar_id"])),
    "vivora_chat": ("Send a text turn; returns tokens, reply text and lip-synced video chunk URLs.", {"session_id": "string", "text": "string", "language": "string?"}, lambda v, a: list(v.chat(a["session_id"], a["text"], a.get("language")))),
}


def _schema(props):
    return {"type": "object", "properties": {k: {"type": "string"} for k in props}, "required": [k for k, t in props.items() if not t.endswith("?")]}


def main():
    v = Vivora()
    for line in sys.stdin:
        if not line.strip():
            continue
        m = json.loads(line)
        mid, method = m.get("id"), m.get("method")
        if mid is None:
            continue
        res, err = None, None
        if method == "initialize":
            res = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "vivora", "version": "0.1.0"}}
        elif method == "tools/list":
            res = {"tools": [{"name": n, "description": d, "inputSchema": _schema(p)} for n, (d, p, _) in TOOLS.items()]}
        elif method == "tools/call":
            n, a = m["params"]["name"], m["params"].get("arguments", {})
            try:
                out = TOOLS[n][2](v, a)
                res = {"content": [{"type": "text", "text": json.dumps(out, default=str)}]}
            except (VivoraError, KeyError) as e:
                res = {"content": [{"type": "text", "text": f"error: {e}"}], "isError": True}
        elif method == "ping":
            res = {}
        else:
            err = {"code": -32601, "message": "method not found"}
        out = {"jsonrpc": "2.0", "id": mid}
        out.update({"error": err} if err else {"result": res})
        sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()
