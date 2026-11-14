"""Does the feature run? Deterministic checks from the logs test.sh wrote, none
of which relies on a name from the spec: the modules are the ones the agent
added (a new __manifest__.py) or changed.
"""

import json
import re
from pathlib import Path

from rewardkit import criterion

LOGS = Path("/logs/verifier")


def _text(name: str) -> str:
    path = LOGS / name
    return path.read_text(errors="replace") if path.exists() else ""


def _exit_code(text: str) -> int | None:
    codes = re.findall(r"^exit code: (\d+)$", text, re.MULTILINE)
    return int(codes[-1]) if codes else None


def _errors(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.search(r" (ERROR|CRITICAL) ", line)]


def _clean_exit(log: str, what: str) -> dict:
    text = _text(log)
    code = _exit_code(text)
    if code == 0:
        return {"score": 1.0, "reasoning": f"{what}: exit code 0"}
    tail = "\n".join(text.splitlines()[-15:])
    return {"score": 0.0, "reasoning": f"{what} failed (exit code {code}):\n{tail}"}


def _check(name: str) -> dict | None:
    for line in _text("odoo_checks.log").splitlines():
        if line.startswith("EVAL_RESULT "):
            result = json.loads(line.removeprefix("EVAL_RESULT "))
            if result.get("check") == name:
                return result
    return None


def _share(name: str, what: str) -> dict:
    result = _check(name)
    if result is None:
        tail = "\n".join(_text("odoo_checks.log").splitlines()[-15:])
        return {"score": 0.0, "reasoning": f"the {what} check did not run:\n{tail}"}
    ok, failed = result["ok"], result["failed"]
    if not ok and not failed:
        return {"score": 0.0, "reasoning": f"the module declares no {what}"}
    score = len(ok) / (len(ok) + len(failed))
    return {"score": score, "reasoning": f"{len(ok)} {what} fine, {len(failed)} failing" + "".join(f"\n- {f}" for f in failed[:10])}


@criterion
def installs(workspace: Path) -> dict:
    return _clean_exit("odoo_install.log", "install without demo data")


@criterion
def installs_with_demo(workspace: Path) -> dict:
    return _clean_exit("odoo_install_demo.log", "install with demo data")


@criterion
def no_errors_logged(workspace: Path) -> dict:
    """An error logged while installing or upgrading counts once, here, not
    once per step that logs it."""
    errors = []
    for log in ("odoo_install.log", "odoo_install_demo.log", "odoo_upgrade.log"):
        # drop the timestamp and pid, so the same error logged by each step shows once
        errors += [re.sub(r"^\S+ \S+ \d+ ", "", line) for line in _errors(_text(log))]
    if not errors:
        return {"score": 1.0, "reasoning": "no ERROR or CRITICAL line while installing or upgrading"}
    unique = list(dict.fromkeys(errors))
    return {"score": 0.0, "reasoning": "errors logged:" + "".join(f"\n- {e}" for e in unique[:8])}


@criterion
def views_load(workspace: Path) -> dict:
    return _share("views", "views")


@criterion
def actions_and_menus_open(workspace: Path) -> dict:
    return _share("actions", "actions and menus")


@criterion
def static_builds(workspace: Path) -> dict:
    result = _check("static")
    js = _text("js_check.log").splitlines()
    js_failed = [line for line in js if line.startswith("FAIL ")]
    failed = (result or {}).get("failed", ["the static check did not run"]) + js_failed
    if failed:
        return {"score": 0.0, "reasoning": "static files broken:" + "".join(f"\n- {f}" for f in failed[:10])}
    return {"score": 1.0, "reasoning": f"static XML parses, backend assets build, {len(js)} JS files pass node --check"}


@criterion
def upgrades(workspace: Path) -> dict:
    return _clean_exit("odoo_upgrade.log", "module upgrade")


def _test_results() -> dict | None:
    path = LOGS / "test_results.json"
    return json.loads(path.read_text()) if path.exists() and path.read_text().strip() else None


def _key(failure: dict) -> tuple:
    return failure["module"], failure["class"], failure["method"]


@criterion
def own_tests_pass(workspace: Path) -> dict:
    """The agent's own tests: every test of a new module, and the tests in the
    test files it added to existing modules."""
    results = _test_results()
    if results is None:
        return {"score": 0.0, "reasoning": "the tests did not run"}
    run, failed = results["own"]["run"], results["own"]["failed"]
    if not run:
        return {"score": 0.0, "reasoning": "the agent wrote no test that ran"}
    names = [f"{f['class']}.{f['method'] or 'setUpClass'}" for f in failed]
    return {
        "score": max(0.0, (run - len(failed)) / run),
        "reasoning": f"{run - len(failed)} of the agent's {run} tests pass" + "".join(f"\n- {n}" for n in names[:10]),
    }


@criterion
def no_regressions(workspace: Path) -> dict:
    """The existing tests of the modules the agent changed still pass: a
    failing one counts only if it passes on the base commit, re-run there with
    the same existing modules installed."""
    results = _test_results()
    if results is None:
        return {"score": 0.0, "reasoning": "the tests did not run"}
    run, failed = results["existing"]["run"], results["existing"]["failed"]
    if not failed:
        return {"score": 1.0, "reasoning": f"no existing test fails ({run} ran)"}
    base_lines = _text("base_failed.jsonl").splitlines()
    base = {_key(json.loads(line)) for line in base_lines if line.strip()}
    base_classes = {(m, c) for m, c, method in base if method is None}

    def also_on_base(f):
        return _key(f) in base or (f["module"], f["class"]) in base_classes

    regressions = [f for f in failed if not also_on_base(f)]
    known = len(failed) - len(regressions)
    if not regressions:
        return {"score": 1.0, "reasoning": f"{len(failed)} existing tests fail, all of them on the base commit too ({run} ran)"}
    names = [f"{f['module']}: {f['class']}.{f['method'] or 'setUpClass'}" for f in regressions]
    return {
        # one broken existing test is a defect on its own, whatever the size
        # of the suite
        "score": 0.0,
        "reasoning": f"{len(regressions)} existing tests the change broke ({known} more fail on the base commit too, {run} ran)"
                     + "".join(f"\n- {n}" for n in names[:10]),
    }
