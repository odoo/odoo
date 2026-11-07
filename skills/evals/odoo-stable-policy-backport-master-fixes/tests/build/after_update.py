"""Once the modules are updated: is the warning gone, do both modules' tests
pass, and does the renaming still work?

test.sh ran `-u l10n_it_stock_ddt,mrp_account` on the agent's code with the
tests of l10n_it_stock_ddt and of mrp_account's TestMrpAccount
(/logs/verifier/odoo_update_tests.log), the agent's own test changes included,
then ran the renaming check again (/logs/verifier/odoo_after_update.log).
"""

import json
import re
from pathlib import Path

from rewardkit import criterion

UPDATE_LOG = Path("/logs/verifier/odoo_update_tests.log")
AFTER_LOG = Path("/logs/verifier/odoo_after_update.log")
WARNING_RE = re.compile(r"Two fields \((\w+), (\w+)\) of stock\.picking\(\) have the same label: ([^.]*)\.")


def _read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


@criterion
def duplicate_label_warning_gone(workspace: Path) -> dict:
    log = _read(UPDATE_LOG)
    if "Modules loaded" not in log:
        tail = "\n".join(log.splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the update did not complete:\n{tail}"}
    found = WARNING_RE.findall(log)
    return {
        "score": 1.0 if not found else 0.0,
        "reasoning": "updating l10n_it_stock_ddt logs no duplicate-label warning on stock.picking"
        if not found else f"the update still warns about fields with the same label: {sorted(set(found))}",
    }


@criterion
def module_tests_pass(workspace: Path) -> dict:
    log = _read(UPDATE_LOG)
    summary = re.findall(r"odoo\.tests\.result: (\d+) failed, (\d+) error\(s\) of (\d+) tests", log)
    failures = re.findall(r"^.*(?:FAIL|ERROR): Test\S+.*$", log, re.MULTILINE)
    if not summary:
        tail = "\n".join(log.splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the tests did not run:\n{tail}"}
    failed, errors, total = map(int, summary[-1])
    ok = total > 0 and failed == 0 and errors == 0
    return {
        "score": 1.0 if ok else 0.0,
        "reasoning": f"{failed} failed, {errors} errors of {total} tests of l10n_it_stock_ddt and mrp_account"
        + ("" if ok else ":\n" + "\n".join(failures[:10])),
    }


@criterion
def renaming_test_ran(workspace: Path) -> dict:
    """The DDT suite still has a test of the renaming scenario, and it passed:
    the test is kept and adapted, not deleted or skipped."""
    log = _read(UPDATE_LOG)
    started = re.findall(r"Starting TestDDT\.(test_\w*sequence\w*)", log)
    failed = re.findall(r"(?:FAIL|ERROR): TestDDT\.(test_\w*sequence\w*)", log)
    skipped = re.findall(r"TestDDT\.(test_\w*sequence\w*).*skipped", log)
    ok = bool(started) and not failed and not skipped
    return {
        "score": 1.0 if ok else 0.0,
        "reasoning": f"TestDDT ran {sorted(set(started))} and it passed" if ok
        else f"no passing DDT sequence test in the run (started: {sorted(set(started))}, failed: {failed}, skipped: {skipped})",
    }


@criterion
def renaming_works_after_update(workspace: Path) -> dict:
    lines = [line for line in _read(AFTER_LOG).splitlines() if line.startswith("EVAL_RESULT ")]
    result = json.loads(lines[-1].removeprefix("EVAL_RESULT ")) if lines else None
    if result is None or result.get("error"):
        tail = "\n".join(_read(AFTER_LOG).splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the check did not run after the update:\n{(result or {}).get('error') or tail}"}
    ok = all(bool(result.get(k)) for k in ("form_view", "rename", "stable_signature"))
    return {
        "score": 1.0 if ok else 0.0,
        "reasoning": "after the update, the form renders and the renaming works through the stable signature"
        if ok else f"after the update: {json.dumps({k: v for k, v in result.items() if k != 'error'})}",
    }
