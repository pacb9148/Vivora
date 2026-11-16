import argparse
import getpass
import json
import subprocess
import sys
from pathlib import Path

from .client import Vivora, VivoraError, load_config, save_config


def main(argv=None):
    p = argparse.ArgumentParser(prog="vivora", description="Vivora live-avatar CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("config", help="set service URL"); a.add_argument("--url", required=True)
    sub.add_parser("status", help="check service health")
    a = sub.add_parser("login"); a.add_argument("--email", default="demo@vivora.app"); a.add_argument("--password")
    a = sub.add_parser("register"); a.add_argument("--email", required=True); a.add_argument("--username", required=True); a.add_argument("--password")
    a = sub.add_parser("avatar-upload"); a.add_argument("file"); a.add_argument("--name", required=True)
    sub.add_parser("avatars")
    a = sub.add_parser("voice-clone"); a.add_argument("audio"); a.add_argument("--name", required=True); a.add_argument("--language", default="en")
    sub.add_parser("voices")
    a = sub.add_parser("session"); a.add_argument("avatar_id")
    a = sub.add_parser("chat"); a.add_argument("session_id"); a.add_argument("text"); a.add_argument("--language")
    a = sub.add_parser("up", help="start local service via docker (needs VIVORA_HOME)")
    a = sub.add_parser("down")
    args = p.parse_args(argv)
    try:
        if args.cmd == "config":
            cfg = load_config(); cfg["url"] = args.url; save_config(cfg); print("ok"); return 0
        if args.cmd in ("up", "down"):
            home = load_config().get("home")
            if not home or not Path(home, "start.sh").exists():
                print("Vivora repo path unknown. Run install-vivora.sh first.", file=sys.stderr); return 1
            return subprocess.call(["./start.sh"] + ([] if args.cmd == "up" else ["--stop"]), cwd=home)
        v = Vivora()
        out = None
        if args.cmd == "status": out = v.health()
        elif args.cmd == "login":
            v.login(args.email, args.password or getpass.getpass("Password: ")); out = {"logged_in": True}
        elif args.cmd == "register":
            out = v.register(args.email, args.username, args.password or getpass.getpass("Password: "))
        elif args.cmd == "avatar-upload": out = v.upload_avatar(args.file, args.name)
        elif args.cmd == "avatars": out = v.avatars()
        elif args.cmd == "voice-clone": out = v.clone_voice(args.audio, args.name, args.language)
        elif args.cmd == "voices": out = v.voices()
        elif args.cmd == "session": out = v.create_session(args.avatar_id)
        elif args.cmd == "chat": out = list(v.chat(args.session_id, args.text, args.language))
        print(json.dumps(out, indent=2, default=str))
        return 0
    except VivoraError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
