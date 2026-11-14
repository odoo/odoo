"""Does the fix reach the emails after a pull and a restart, without a module update?

On a stable branch, a fix must work on databases that are not updated: their
QWeb views and data records stay as they were installed. test.sh installed
test_mail with the base code, then started the agent's code on that database
as is and had a follower notified of a tracking change
(/logs/verifier/odoo_no_update.log).
"""

import json
from pathlib import Path

from rewardkit import criterion

LOG = Path("/logs/verifier/odoo_no_update.log")


def _eval_result(log: Path) -> dict | None:
    text = log.read_text(errors="replace") if log.exists() else ""
    lines = [line for line in text.splitlines() if line.startswith("EVAL_RESULT ")]
    return json.loads(lines[-1].removeprefix("EVAL_RESULT ")) if lines else None


@criterion
def email_fixed_without_update(workspace: Path) -> dict:
    result = _eval_result(LOG)
    if result is None or result.get("error"):
        tail = "\n".join((LOG.read_text(errors="replace") if LOG.exists() else "").splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the agent's code did not run on a database that was not updated:\n{(result or {}).get('error') or tail}"}
    ok = bool(result.get("separators"))
    return {
        "score": 1.0 if ok else 0.0,
        "reasoning": (
            f"without a module update, the tracking email reads {result.get('line')!r}"
            + ("" if ok else ": the fix only works once the module is updated")
        ),
    }
