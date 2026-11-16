export type VivoraEvent = { type: string; [k: string]: any };

export class Vivora {
  constructor(public url = "http://localhost:8000", public token?: string) {
    this.url = url.replace(/\/$/, "");
  }

  private async req<T = any>(method: string, path: string, body?: BodyInit, headers: Record<string, string> = {}, auth = true): Promise<T> {
    if (auth && this.token) headers.Authorization = `Bearer ${this.token}`;
    const r = await fetch(this.url + path, { method, body, headers });
    if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}: ${await r.text()}`);
    const t = await r.text();
    return (t ? JSON.parse(t) : null) as T;
  }
  private json = (o: unknown) => ({ body: JSON.stringify(o), headers: { "Content-Type": "application/json" } });

  health() { return this.req("GET", "/health", undefined, {}, false); }
  register(email: string, username: string, password: string) {
    const j = this.json({ email, username, password });
    return this.req("POST", "/api/v1/users/register", j.body, j.headers, false);
  }
  async login(email: string, password: string) {
    const r = await this.req<{ access_token: string }>("POST", "/api/v1/users/login", new URLSearchParams({ username: email, password }), {}, false);
    this.token = r.access_token;
    return this.token;
  }
  me() { return this.req("GET", "/api/v1/users/me"); }

  /** file: a File/Blob (browser, Node 20+). */
  uploadAvatar(file: Blob, name: string, filename = (file as File).name ?? "avatar") {
    const f = new FormData(); f.set("name", name); f.set("file", file, filename);
    return this.req("POST", "/api/v1/avatars/upload", f);
  }
  avatars() { return this.req<any[]>("GET", "/api/v1/avatars/"); }
  deleteAvatar(id: string) { return this.req("DELETE", `/api/v1/avatars/${id}`); }
  cloneVoice(audio: Blob, name: string, language = "en", filename = (audio as File).name ?? "voice.wav") {
    const f = new FormData(); f.set("name", name); f.set("language", language); f.set("audio", audio, filename);
    return this.req("POST", "/api/v1/voices/clone", f);
  }
  voices() { return this.req<any[]>("GET", "/api/v1/voices/"); }
  setAvatarVoice(avatarId: string, voiceId: string) {
    return this.req("PUT", `/api/v1/avatars/${avatarId}/voice?voice_id=${encodeURIComponent(voiceId)}`);
  }
  createSession(avatarId: string, settings?: object) {
    const j = this.json({ avatar_id: avatarId, settings });
    return this.req<{ id: string }>("POST", "/api/v1/sessions/create", j.body, j.headers);
  }
  endSession(id: string) { return this.req("POST", `/api/v1/sessions/${id}/end`); }
  messages(sessionId: string) { return this.req<any[]>("GET", `/api/v1/messages/session/${sessionId}`); }

  /** Open the realtime socket; call .send({type:"text",text}) and read events via onEvent. */
  connect(sessionId: string, onEvent: (e: VivoraEvent) => void) {
    const ws = new WebSocket(`${this.url.replace(/^http/, "ws")}/ws/session/${sessionId}?token=${encodeURIComponent(this.token ?? "")}`);
    ws.onmessage = (m) => onEvent(JSON.parse(String(m.data)));
    const ready = new Promise<void>((res, rej) => { ws.onopen = () => res(); ws.onerror = () => rej(new Error("WS connection failed")); });
    return { ready, send: (o: VivoraEvent) => ws.send(JSON.stringify(o)), close: () => ws.close() };
  }

  /** One-shot text turn: resolves with all events once the video stream ends. */
  async chat(sessionId: string, text: string): Promise<VivoraEvent[]> {
    const events: VivoraEvent[] = [];
    return new Promise(async (resolve, reject) => {
      const c = this.connect(sessionId, (e) => {
        events.push(e);
        if (e.type === "video_chunk_end" || e.type === "error") { c.close(); resolve(events); }
      });
      try { await c.ready; c.send({ type: "text", text }); } catch (err) { reject(err); }
    });
  }
}
