"""Is the mrp fix in the tree? The patch is the one real master fix of the
three; it has no stable-policy catch, so applying it as is is right. Its tests
run with the module tests in after_update.py.
"""

from pathlib import Path

from rewardkit import criterion

APP = Path("/app")
REPORT = "addons/mrp/report/mrp_report_mo_overview.py"
VIEW = "addons/mrp/views/mrp_production_views.xml"
TEST = "addons/mrp_account/tests/test_mrp_account.py"


def _result(ok: bool, yes: str, no: str) -> dict:
    return {"score": 1.0 if ok else 0.0, "reasoning": yes if ok else no}


def _head(path: str) -> str:
    file = APP / path
    return file.read_text() if file.exists() else ""


@criterion
def mrp_fix_applied(workspace: Path) -> dict:
    missing = []
    if "production.product_id)[:1])" not in _head(REPORT):
        missing.append("the [:1] on the finished move in _get_mo_summary")
    if "('id', '!=', parent.product_id)" not in _head(VIEW):
        missing.append("the by-product domain excluding the MO's product")
    if "def test_finished_product_cannot_be_own_byproduct" not in _head(TEST):
        missing.append("the test of mrp_account")
    return _result(
        not missing,
        "the three hunks of the mrp fix are in the tree",
        "the mrp fix is not fully applied, missing: " + "; ".join(missing),
    )
