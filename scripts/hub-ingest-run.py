#!/usr/bin/env python3
"""
Apply a luffy-run payload onto memory/repos/{owner}--{repo}/ and prepare a commit.

Reads CLIENT_PAYLOAD JSON from env (object with key "run" or the run object itself).
Writes files under repo root (cwd should be hub checkout).
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_MEMORY_BYTES = int(os.environ.get("MAX_MEMORY_BYTES", "200000"))


def slugify_repo(source_repo: str) -> str:
    # owner/name -> owner--name
    s = source_repo.strip().replace("\\", "/")
    if "/" not in s:
        s = f"unknown/{s}"
    owner, name = s.split("/", 1)
    owner = re.sub(r"[^A-Za-z0-9._-]+", "-", owner)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    return f"{owner}--{name}"


def rotate_memory(text: str, max_bytes: int) -> str:
    data = text.encode("utf-8")
    if len(data) <= max_bytes:
        return text if text.endswith("\n") else text + "\n"
    text = data[-max_bytes:].decode("utf-8", errors="ignore")
    idx = text.find("\n## ")
    if idx > 0:
        text = (
            "# Luffy review memory\n\n_(older entries rotated)_\n" + text[idx:]
        )
    else:
        text = "# Luffy review memory\n\n_(rotated)_\n" + text
    return text if text.endswith("\n") else text + "\n"


def main() -> int:
    raw = os.environ.get("CLIENT_PAYLOAD") or os.environ.get("LUFFY_RUN_PAYLOAD")
    if not raw:
        # Allow file path
        path = os.environ.get("CLIENT_PAYLOAD_FILE")
        if path and Path(path).exists():
            raw = Path(path).read_text()
        else:
            print("CLIENT_PAYLOAD missing", file=sys.stderr)
            return 1

    data = json.loads(raw)
    run = data.get("run") if isinstance(data, dict) and "run" in data else data
    if not isinstance(run, dict):
        print("invalid payload shape", file=sys.stderr)
        return 1

    source_repo = run.get("source_repo") or "unknown/unknown"
    slug = slugify_repo(source_repo)
    pr = str(run.get("pr_number") or "unknown")
    trace_id = str(run.get("trace_id") or f"pr{pr}-run{run.get('run_id', 'unknown')}")
    # sanitize trace_id for path
    safe_trace = re.sub(r"[^A-Za-z0-9._-]+", "-", trace_id)

    root = Path(os.environ.get("HUB_ROOT", ".")).resolve()
    repo_dir = root / "memory" / "repos" / slug
    run_dir = repo_dir / "runs" / safe_trace
    run_dir.mkdir(parents=True, exist_ok=True)

    review_md = run.get("review_md") or ""
    memory_block = run.get("memory_block") or ""
    meta = {
        "ingested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_repo": source_repo,
        "slug": slug,
        "trace_id": trace_id,
        "pr_number": pr,
        "run_id": run.get("run_id"),
        "run_attempt": run.get("run_attempt"),
        "model": run.get("model"),
        "status": run.get("status"),
        "verdict": run.get("verdict"),
        "review_truncated": run.get("review_truncated"),
        "timings": run.get("timings") or {},
        "meta": run.get("meta") or {},
        "schema_version": run.get("schema_version", 1),
    }

    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    if review_md:
        (run_dir / "review.md").write_text(
            review_md if review_md.endswith("\n") else review_md + "\n"
        )
    if memory_block:
        (run_dir / "summary.md").write_text(
            memory_block if memory_block.endswith("\n") else memory_block + "\n"
        )

    # latest pointer
    (repo_dir / "latest.json").write_text(
        json.dumps(
            {
                "trace_id": trace_id,
                "pr_number": pr,
                "verdict": run.get("verdict"),
                "status": run.get("status"),
                "ingested_at": meta["ingested_at"],
                "run_path": f"memory/repos/{slug}/runs/{safe_trace}",
            },
            indent=2,
        )
        + "\n"
    )

    memory_file = repo_dir / "MEMORY.md"
    if memory_file.exists():
        existing = memory_file.read_text(errors="replace")
    else:
        existing = (
            f"# Luffy review memory — `{source_repo}`\n\n"
            "Cumulative notes from Luffy PR reviews (hub-ingested).\n"
        )

    if memory_block and memory_block.strip() not in existing:
        existing = existing.rstrip() + "\n\n" + memory_block.strip() + "\n"
    existing = rotate_memory(existing, MAX_MEMORY_BYTES)
    memory_file.write_text(existing)

    # index of all known repos
    index_path = root / "memory" / "index.json"
    repos = []
    repos_root = root / "memory" / "repos"
    if repos_root.exists():
        for p in sorted(repos_root.iterdir()):
            if p.is_dir() and (p / "MEMORY.md").exists():
                latest = {}
                lf = p / "latest.json"
                if lf.exists():
                    try:
                        latest = json.loads(lf.read_text())
                    except json.JSONDecodeError:
                        latest = {}
                repos.append(
                    {
                        "slug": p.name,
                        "path": f"memory/repos/{p.name}",
                        "latest": latest,
                    }
                )
    index_path.write_text(
        json.dumps(
            {
                "updated_at": meta["ingested_at"],
                "repos": repos,
            },
            indent=2,
        )
        + "\n"
    )

    # Export for commit message
    summary_path = root / ".luffy-ingest-summary.txt"
    summary_path.write_text(
        f"ingest {source_repo} PR #{pr} trace={trace_id} verdict={run.get('verdict')}\n"
    )
    print(f"Wrote memory for {slug} trace={safe_trace}")
    print(f"MEMORY={memory_file}")
    print(f"RUN_DIR={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
