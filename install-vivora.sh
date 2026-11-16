#!/usr/bin/env bash
# Instalar Vivora: servicio (Docker) + cliente Python/CLI + cliente TS + skill + MCP para todos los agentes.
# Uso: ./install-vivora.sh [--all] [--service] [--clients] [--skills] [--url URL]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DO_SERVICE=0; DO_CLIENTS=0; DO_SKILLS=0; URL=""
[ $# -eq 0 ] && set -- --clients --skills
while [ $# -gt 0 ]; do case "$1" in
  --all) DO_SERVICE=1; DO_CLIENTS=1; DO_SKILLS=1;;
  --service) DO_SERVICE=1;; --clients) DO_CLIENTS=1;; --skills) DO_SKILLS=1;;
  --url) URL="$2"; shift;; -h|--help) sed -n 2,3p "$0"; exit 0;;
  *) echo "Opción desconocida: $1" >&2; exit 1;; esac; shift; done

mkdir -p "$HOME/.vivora"
CFG="$HOME/.vivora/config.json"
python3 - "$CFG" "$HERE" "$URL" <<'PY'
import json,sys,os
p,home,url=sys.argv[1:4]
c=json.load(open(p)) if os.path.exists(p) else {}
c["home"]=home
if url: c["url"]=url
c.setdefault("url","http://localhost:8000")
json.dump(c,open(p,"w"),indent=2); os.chmod(p,0o600)
PY
echo "✔ Config: $CFG"

if [ $DO_CLIENTS = 1 ]; then
  if command -v pipx >/dev/null; then pipx install --force "$HERE/integrations/python[chat]" >/dev/null
  elif [ -n "${VIRTUAL_ENV:-}" ]; then python3 -m pip install -q -e "$HERE/integrations/python[chat]"
  else python3 -m pip install --user -q --break-system-packages -e "$HERE/integrations/python[chat]" 2>/dev/null || python3 -m pip install --user -q -e "$HERE/integrations/python[chat]"; fi
  echo "✔ Cliente Python + CLI 'vivora' + MCP 'vivora-mcp'"
  if command -v npm >/dev/null; then
    (cd "$HERE/integrations/typescript" && npm install --silent && npm run build --silent)
    echo "✔ Cliente TypeScript construido. En un proyecto: npm install $HERE/integrations/typescript"
  else echo "• npm no encontrado: cliente TS omitido"; fi
fi

if [ $DO_SKILLS = 1 ]; then
  for d in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.codex/skills" "$HOME/.cursor/skills"; do
    mkdir -p "$d" && rm -rf "$d/vivora" && cp -r "$HERE/integrations/skill/vivora" "$d/vivora" && echo "✔ Skill → $d/vivora"
  done
  cp "$HERE/integrations/AGENTS.md" "$HOME/.vivora/AGENTS.md"
  if command -v claude >/dev/null; then
    claude mcp add --scope user vivora -- vivora-mcp >/dev/null 2>&1 && echo "✔ MCP registrado en Claude Code (todos los proyectos)" || echo "• MCP ya registrado o falló: claude mcp add --scope user vivora -- vivora-mcp"
  fi
  echo "• Otros agentes (MCP): {\"mcpServers\":{\"vivora\":{\"command\":\"vivora-mcp\"}}}"
fi

if [ $DO_SERVICE = 1 ]; then
  command -v docker >/dev/null || { echo "Docker no encontrado" >&2; exit 1; }
  (cd "$HERE" && ./start.sh)
fi
echo "Listo. Verifica con: vivora status"
