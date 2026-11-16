# Vivora API (base: $VIVORA_URL, default http://localhost:8000)
Auth: `POST /api/v1/users/login` (form: username=email, password) → `{access_token}`; send `Authorization: Bearer <token>`.
- `POST /api/v1/users/register` {email, username, password}
- `POST /api/v1/avatars/upload` multipart: file, name · `GET /api/v1/avatars/` · `GET|DELETE /api/v1/avatars/{id}` · `PUT /api/v1/avatars/{id}/voice?voice_id=`
- `POST /api/v1/voices/clone` multipart: audio, name, language · `GET /api/v1/voices/`
- `POST /api/v1/sessions/create` {avatar_id} · `POST /api/v1/sessions/{id}/end` · `GET /api/v1/messages/session/{id}`
- `WS /ws/session/{id}?token=<jwt>`: send `{type:text,text}` `{type:audio,audio:b64}` `{type:stop}` `{type:set_voice,voice_id}` `{type:set_language,language}`; receive `token`, `transcription`, `message`, `video_chunk_start|video_chunk|video_chunk_end`, `status`, `interrupted`, `error`.
Docs: `/docs`.
