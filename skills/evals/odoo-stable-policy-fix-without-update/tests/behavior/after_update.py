"""Once mail is updated, is the email right, and do the tracking tests pass?

test.sh ran `-u mail` on the agent's code and checked the tracking email again
(/logs/verifier/odoo_update.log), then ran the tracking tests of test_mail
(/logs/verifier/odoo_tests.log), with the agent's own test changes.
"""

import json
import re
from pathlib import Path

from rewardkit import criterion

UPDATE_LOG = Path("/logs/verifier/odoo_update.log")
TESTS_LOG = Path("/logs/verifier/odoo_tests.log")


def _read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


@criterion
def email_fixed_after_update(workspace: Path) -> dict:
    lines = [line for line in _read(UPDATE_LOG).splitlines() if line.startswith("EVAL_RESULT ")]
    result = json.loads(lines[-1].removeprefix("EVAL_RESULT ")) if lines else None
    if result is None or result.get("error"):
        tail = "\n".join(_read(UPDATE_LOG).splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the check did not run after `-u mail`:\n{(result or {}).get('error') or tail}"}
    ok = bool(result.get("separators"))
    return {
        "score": 1.0 if ok else 0.0,
        "reasoning": f"after `-u mail`, the tracking email reads {result.get('line')!r}"
        + ("" if ok else " (expected 'Old Box -> New Box (Container)', the arrow once)"),
    }


@criterion
def tracking_tests_pass(workspace: Path) -> dict:
    log = _read(TESTS_LOG)
    summary = re.findall(r"odoo\.tests\.result: (\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    failures = re.findall(r"^.*(?:FAIL|ERROR): Test\S+.*$", log, re.MULTILINE)
    if not summary:
        tail = "\n".join(log.splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the tracking tests did not run:\n{tail}"}
    failed, errors, total = map(int, summary[-1])
    ok = total > 0 and failed == 0 and errors == 0
    return {
        "score": 1.0 if ok else 0.0,
        "reasoning": f"{failed} failed, {errors} errors of {total} tracking tests"
        + ("" if ok else ":\n" + "\n".join(failures[:10])),
    }
