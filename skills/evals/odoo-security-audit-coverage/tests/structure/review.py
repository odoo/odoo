"""Did the agent write the review and leave the module as it was?

Reads the snapshot test.sh wrote under /logs/verifier/.
"""

from pathlib import Path

from rewardkit import criterion

OUT = Path("/logs/verifier")


def _read(name: str) -> str:
    path = OUT / name
    return path.read_text() if path.exists() else ""


def _result(ok: bool, yes: str, no: str) -> dict:
    return {"score": 1.0 if ok else 0.0, "reasoning": yes if ok else no}


@criterion
def review_written(workspace: Path) -> dict:
    review = _read("security_review.md").strip()
    return _result(
        bool(review),
        f"/app/security_review.md has {len(review.splitlines())} lines",
        "/app/security_review.md is missing or empty",
    )


@criterion
def module_untouched(workspace: Path) -> dict:
    changes = _read("module_changes.txt").strip()
    return _result(
        not changes,
        "addons/property_rental is unchanged and no commit was added",
        f"the module or the branch changed:\n{changes}",
    )
