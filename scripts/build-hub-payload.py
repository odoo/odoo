#!/usr/bin/env python3
"""Build a size-capped JSON payload for hub repository_dispatch (luffy-run)."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

MAX_REVIEW_CHARS = int(os.environ.get("LUFFY_HUB_MAX_REVIEW_CHARS", "14000"))
MAX_SUMMARY_CHARS = int(os.environ.get("LUFFY_HUB_MAX_SUMMARY_CHARS", "4000"))
MAX_TRIGGER_CHARS = 500


def redact(text: str) -> str:
    text = re.sub(r"sk-or-v1-[A-Za-z0-9_-]{10,}", "[OPENROUTER_KEY_REDACTED]", text)
    text = re.sub(r"(OPENROUTER_API_KEY=)\S+", r"\1[REDACTED]", text)
    return text


def extract_verdict(review: str) -> str:
    for line in review.splitlines():
        if line.strip().startswith("**Verdict:**"):
            return line.split("**Verdict:**", 1)[-1].strip()
    return "unknown"


def extract_section(review: str, heading: str) -> str:
    lines = review.splitlines()
    out: list[str] = []
    in_sec = False
    for line in lines:
        if line.strip().startswith("### ") and in_sec:
            break
        if line.strip().startswith(heading):
            in_sec = True
            continue
        if in_sec:
            out.append(line)
    return "\n".join(out).strip()


def main() -> int:
    out_dir = Path(os.environ.get("OUT_DIR", ".luffy-out"))
    pr = os.environ.get("PR_NUMBER", "unknown")
    repo = os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or "unknown/unknown"
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    model = os.environ.get("LUFFY_MODEL") or os.environ.get("OPENROUTER_MODEL") or "unknown"
    status = os.environ.get("LUFFY_STATUS", "unknown")
    trigger = (os.environ.get("TRIGGER_COMMENT") or "")[:MAX_TRIGGER_CHARS]
    trace_id = os.environ.get("TRACE_ID") or f"pr{pr}-run{run_id}-a{attempt}"

    review_path = out_dir / f"review-{pr}.md"
    if not review_path.exists():
        candidates = sorted(out_dir.glob("review-*.md"), reverse=True)
        candidates = [p for p in candidates if ".raw." not in p.name]
        review_path = candidates[0] if candidates else None

    review = ""
    if review_path and review_path.exists():
        review = redact(review_path.read_text(errors="replace"))

    truncated = False
    if len(review) > MAX_REVIEW_CHARS:
        review = review[:MAX_REVIEW_CHARS] + "\n\n… [truncated for hub payload] …\n"
        truncated = True

    verdict = extract_verdict(review) if review else "unknown"
    blocking = extract_section(review, "### Blocking") if review else ""
    summary_body = extract_section(review, "### Summary") if review else ""

    memory_block = redact(
        f"""## Review run {trace_id}
- Source: `{repo}` PR #{pr}
- Status: {status}
- Model: {model}
- Verdict: {verdict}
- Blocking: {(blocking or "None").replace(chr(10), " ")[:500]}
- Summary: {(summary_body or "").replace(chr(10), " ")[:800]}
- Trigger: {trigger[:200]}
"""
    )
    if len(memory_block) > MAX_SUMMARY_CHARS:
        memory_block = memory_block[:MAX_SUMMARY_CHARS] + "\n…\n"

    meta = {}
    meta_path = out_dir / "meta.env"
    # Prefer trace meta.json if present
    latest = out_dir / "latest-trace-dir.txt"
    if latest.exists():
        tdir = Path(latest.read_text().strip())
        mj = tdir / "meta.json"
        if mj.exists():
            try:
                meta = json.loads(mj.read_text())
            except json.JSONDecodeError:
                meta = {}
        if not os.environ.get("TRACE_ID") and meta.get("trace_id"):
            trace_id = meta["trace_id"]

    timings = {}
    tj = out_dir / "timings.json"
    if tj.exists():
        try:
            timings = json.loads(tj.read_text())
        except json.JSONDecodeError:
            timings = {}

    payload = {
        "schema_version": 1,
        "event": "luffy-run",
        "source_repo": repo,
        "pr_number": str(pr),
        "run_id": str(run_id),
        "run_attempt": str(attempt),
        "trace_id": trace_id,
        "model": model,
        "status": status,
        "verdict": verdict,
        "trigger_comment": trigger,
        "review_truncated": truncated,
        "review_md": review,
        "memory_block": memory_block,
        "timings": timings,
        "meta": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_ref": os.environ.get("GITHUB_REF"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
            "started_at": os.environ.get("LUFFY_STARTED_AT"),
            "trace_meta": meta if isinstance(meta, dict) else {},
        },
    }

    dest = out_dir / "hub-payload.json"
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    # Size guard (~20KB soft)
    size = dest.stat().st_size
    if size > 20_000:
        # Shrink review harder
        payload["review_md"] = payload["review_md"][:8000] + "\n\n… [hard truncated] …\n"
        payload["review_truncated"] = True
        dest.write_text(json.dumps(payload, indent=2) + "\n")
        size = dest.stat().st_size
    print(dest)
    print(f"payload_bytes={size}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
