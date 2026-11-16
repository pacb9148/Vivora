---
name: vivora
description: Use Vivora to add live, lip-synced talking-avatar conversations (photo/video avatar, voice cloning, streaming chat) to any project. Use when the user wants an avatar that speaks, voice cloning, or to integrate/call the Vivora API.
---

# Vivora

Vivora is a self-hosted service (FastAPI + Next.js). Projects use it through its REST/WebSocket API; never copy its source into the project.

## Setup (once per machine)
- Service URL/token live in `~/.vivora/config.json` (or env `VIVORA_URL`, `VIVORA_TOKEN`).
- Check: `vivora status`. If unreachable: `vivora up` (Docker) or ask the user for the deployed URL and run `vivora config --url <url>`.
- Auth: `vivora login --email demo@vivora.app` (demo password is shown on the app login screen / README) or `vivora register`.

## Use from a project
- Python: `pip install -e <vivora-repo>/integrations/python` → `from vivora_client import Vivora`
- TypeScript/JS: `npm install <vivora-repo>/integrations/typescript` → `import { Vivora } from "vivora-client"`
- Any MCP agent: server command `vivora-mcp` (tools: vivora_status, vivora_list_avatars, vivora_upload_avatar, vivora_clone_voice, vivora_list_voices, vivora_create_session, vivora_chat).
- Raw API: see `API.md` in this folder.

## Typical flow
1. `upload_avatar(photo_or_video, name)` → avatar id
2. optional `clone_voice(audio, name)` → `set_avatar_voice(avatar_id, voice_id)`
3. `create_session(avatar_id)` → session id
4. `chat(session_id, "text")` → events: `token` (stream), `message`, `video_chunk` (`video_url`), `video_chunk_end`

## Rules
- Lip-sync needs MuseTalk weights (`bash scripts/setup_musetalk.sh`) and ideally a GPU; otherwise avatars show a still image.
- Verify with `vivora status` before assuming it works; report real errors.
