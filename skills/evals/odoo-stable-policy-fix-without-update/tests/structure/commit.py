"""Did the agent commit its fix as one commit, leaving nothing behind, on its branch?

Reads the snapshot test.sh wrote under /logs/verifier/ and the checkout in /app.
"""

import subprocess
from pathlib import Path

from rewardkit import criterion

OUT = Path("/logs/verifier")
BRANCH = "20.0-mail-tracking-arrows-jdoe"


def _read(name: str) -> str:
    path = OUT / name
    return path.read_text() if path.exists() else ""


def _result(ok: bool, yes: str, no: str) -> dict:
    return {"score": 1.0 if ok else 0.0, "reasoning": yes if ok else no}


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
