"""Does the fix hold on a database that was not updated? (the stable deployment)

On a stable branch, a fix must work on databases that run the new code after a
pull and a restart: their views stay as installed, and their extension modules
call the methods as they were. test.sh installed l10n_it_stock_ddt and
mrp_account with the base code, then ran the agent's code on that database as
is (/logs/verifier/odoo_no_update.log): the installed picking form, which
references l10n_it_country_code, must still render, and the DDT sequence
renaming of the failing test must work, through _get_dtt_ir_seq_vals called
with an id as 20.0 defines it.
"""

import json
from pathlib import Path

from rewardkit import criterion

LOG = Path("/logs/verifier/odoo_no_update.log")


def _eval_result(log: Path) -> dict | None:
    text = log.read_text(errors="replace") if log.exists() else ""
    lines = [line for line in text.splitlines() if line.startswith("EVAL_RESULT ")]
    return json.loads(lines[-1].removeprefix("EVAL_RESULT ")) if lines else None


def _check(key: str, yes: str, no: str) -> dict:
    result = _eval_result(LOG)
    if result is None or result.get("error"):
        tail = "\n".join((LOG.read_text(errors="replace") if LOG.exists() else "").splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the agent's code did not run on a database that was not updated:\n{(result or {}).get('error') or tail}"}
    ok = bool(result.get(key))
    detail = result.get(key + "_error") or result.get("renamed")
    return {"score": 1.0 if ok else 0.0, "reasoning": yes if ok else f"{no}: {detail}"}


@criterion
def installed_form_still_renders(workspace: Path) -> dict:
    return _check(
        "form_view",
        "the picking form installed with the base code renders with the new code",
        "the picking form installed with the base code no longer renders (it references l10n_it_country_code)",
    )


@criterion
def sequence_renaming_works(workspace: Path) -> dict:
    return _check(
        "rename",
        "renaming a delivery type's prefix together with its warehouse renames its DDT sequence",
        "renaming a delivery type's prefix together with its warehouse does not give 'Milano Sequence MOUT' / 'MOUTDDT'",
    )


@criterion
def method_still_takes_an_id(workspace: Path) -> dict:
    result = _eval_result(LOG) or {}
    both = bool(result.get("stable_signature")) and bool(result.get("stable_signature_no_warehouse"))
    if result.get("error") or not result:
        return _check("stable_signature", "", "")
    detail = result.get("stable_signature_error") or result.get("stable_signature_no_warehouse_error")
    return {
        "score": 1.0 if both else 0.0,
        "reasoning": "_get_dtt_ir_seq_vals still works when called with a warehouse id, and with none, as its callers do"
        if both else f"_get_dtt_ir_seq_vals no longer works when called with a warehouse id as 20.0's callers and overrides do: {detail}",
    }
