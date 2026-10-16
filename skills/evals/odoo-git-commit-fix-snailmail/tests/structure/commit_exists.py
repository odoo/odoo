"""Did the agent make exactly one commit carrying the pending change, and nothing else?

Reads the snapshot test.sh wrote under /logs/verifier/ and the checkout in /app.
"""

import re
import subprocess
from pathlib import Path

from rewardkit import criterion

OUT = Path("/logs/verifier")
EXPECTED_PATCH = Path("/tests/change.patch")
BRANCH = "20.0-snailmail-cover-fva"


def _read(name: str) -> str:
    path = OUT / name
    return path.read_text() if path.exists() else ""


def _result(ok: bool, yes: str, no: str) -> dict:
    return {"score": 1.0 if ok else 0.0, "reasoning": yes if ok else no}


def _normalize_diff(text: str) -> str:
    # The blob hashes of the index lines differ between checkouts; the rest must match.
    lines = [line.rstrip() for line in text.splitlines() if not line.startswith("index ")]
    return "\n".join(lines).strip()


@criterion
def one_new_commit(workspace: Path) -> dict:
    commits = _read("new_commits.txt").split()
    headers = _read("commit_headers.txt").strip()
    return _result(
        len(commits) == 1,
        f"one commit on top of the base: {headers}",
        f"{len(commits)} commits on top of the base (expected 1): {headers or 'none'}",
    )


@criterion
def working_tree_clean(workspace: Path) -> dict:
    status = _read("status.txt").strip()
    return _result(
        not status,
        "nothing left uncommitted",
        f"uncommitted changes remain:\n{status}",
    )


@criterion
def change_committed_as_is(workspace: Path) -> dict:
    got = _normalize_diff(_read("commit.diff"))
    want = _normalize_diff(EXPECTED_PATCH.read_text())
    return _result(
        got == want,
        "the commit diff equals the pending change",
        "the commit diff differs from the pending change (code was altered, dropped, or files added)",
    )


@criterion
def branch_unchanged(workspace: Path) -> dict:
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=workspace, capture_output=True, text=True
    )
    branch = proc.stdout.strip()
    return _result(
        branch == BRANCH,
        f"still on {BRANCH}",
        f"HEAD is on {branch!r}, expected {BRANCH}",
    )
