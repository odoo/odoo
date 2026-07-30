#!/usr/bin/env bash
# Append a structured memory block after a review (grows MEMORY.md).
#
# Env:
#   HERMES_HOME (or LUFFY_ROOT/.luffy-hermes-home)
#   OUT_DIR with meta.env + review-*.md
#   MAX_MEMORY_BYTES (default: 100000)
set -euo pipefail

log() { echo "$*" >&2; }

LUFFY_ROOT="${LUFFY_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HERMES_HOME="${HERMES_HOME:-$LUFFY_ROOT/.luffy-hermes-home}"
OUT_DIR="${OUT_DIR:-$LUFFY_ROOT/.luffy-out}"
MAX_MEMORY_BYTES="${MAX_MEMORY_BYTES:-100000}"

mkdir -p "$HERMES_HOME/memories"
MEMORY_FILE="$HERMES_HOME/memories/MEMORY.md"

if [[ -f "$OUT_DIR/meta.env" ]]; then
  # shellcheck disable=SC1091
  source "$OUT_DIR/meta.env"
fi

PR_NUMBER="${PR_NUMBER:-?}"
PR_TITLE="${PR_TITLE:-}"
REPO="${REPO:-}"
REVIEW_FILE="${REVIEW_FILE:-}"

if [[ -z "$REVIEW_FILE" ]]; then
  if compgen -G "$OUT_DIR/review-*.md" >/dev/null; then
    # Prefer normalized final, not .raw
    REVIEW_FILE="$(ls -t "$OUT_DIR"/review-*.md 2>/dev/null | grep -v '\.raw\.md$' | head -1 || true)"
  fi
fi

[[ -n "${REVIEW_FILE:-}" && -f "$REVIEW_FILE" ]] || {
  log "No review file; skip memory distill"
  exit 0
}

[[ -f "$MEMORY_FILE" ]] || cp -f "$LUFFY_ROOT/agent/MEMORY.seed.md" "$MEMORY_FILE" 2>/dev/null || \
  printf '# Luffy review memory\n\n' >"$MEMORY_FILE"

DATE_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Extract verdict line if present
VERDICT="$(grep -E '^\*\*Verdict:\*\*' "$REVIEW_FILE" | head -1 | sed 's/.*\*\*Verdict:\*\*[[:space:]]*//' || true)"
BLOCKING="$(python3 - <<'PY' "$REVIEW_FILE"
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text(errors="replace").splitlines()
in_b = False
lines = []
for line in text:
    if line.strip().startswith("### Blocking"):
        in_b = True
        continue
    if in_b and line.startswith("### "):
        break
    if in_b:
        s = line.strip()
        if s.startswith("-"):
            lines.append(s)
print("; ".join(lines[:5]) if lines else "None")
PY
)"

python3 - <<'PY' "$MEMORY_FILE" "$MAX_MEMORY_BYTES" "$DATE_UTC" "$REPO" "$PR_NUMBER" "$PR_TITLE" "$VERDICT" "$BLOCKING"
from pathlib import Path
import sys

path = Path(sys.argv[1])
max_bytes = int(sys.argv[2])
date, repo, pr, title, verdict, blocking = sys.argv[3:9]

block = f"""
## Review {date} · {repo} PR #{pr} · {title}

- Verdict: {verdict or "unknown"}
- Blocking notes: {blocking or "None"}
- (Auto-distilled; refine manually if needed)

"""

text = path.read_text(errors="replace") if path.exists() else "# Luffy review memory\n"
text = text.rstrip() + "\n" + block
data = text.encode("utf-8")
if len(data) > max_bytes:
    # Keep header + tail
    text = text.encode("utf-8")[-max_bytes:].decode("utf-8", errors="ignore")
    # Align to next section if possible
    idx = text.find("\n## ")
    if idx > 0:
        text = "# Luffy review memory\n\n_(older entries rotated)_\n" + text[idx:]
    else:
        text = "# Luffy review memory\n\n_(rotated)_\n" + text
path.write_text(text if text.endswith("\n") else text + "\n")
print(path)
PY

log "Memory distilled → $MEMORY_FILE ($(wc -c <"$MEMORY_FILE" | tr -d ' ') bytes)"
