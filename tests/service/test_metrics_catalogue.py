"""The deployment view's `/web/metrics` table names every family the
exposition renders, and nothing it does not."""

import pathlib
import re

from odoo.service import metrics

DOC = pathlib.Path(__file__).resolve().parents[2] / "doc/architecture/deployment.md"
SOURCE = pathlib.Path(metrics.__file__)

_DYNAMIC_PREFIX = "odoo_db_pool_"


def _rendered_families() -> set[str]:
    source = SOURCE.read_text(encoding="utf-8")
    names = set(re.findall(r'"(odoo_[a-z_]+)"', source))
    assert names, "the source names no family; the scan is broken"
    if re.search(r'f"odoo_db_pool_\{', source):
        names.add(_DYNAMIC_PREFIX + "<stat>")
    return names


def _section() -> str:
    text = DOC.read_text(encoding="utf-8")
    start = text.index("## What `/web/metrics` exposes")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def _documented_families() -> set[str]:
    return set(re.findall(r"`(odoo_[a-z_<>]+)`", _section()))


def test_every_rendered_family_is_documented():
    missing = _rendered_families() - _documented_families()
    assert not missing, (
        f"rendered by odoo/service/metrics.py and absent from the table in "
        f"{DOC.name}: {sorted(missing)}"
    )


def test_every_documented_family_is_rendered():
    stale = _documented_families() - _rendered_families()
    assert not stale, f"listed in {DOC.name} and rendered by nothing: {sorted(stale)}"


def test_the_scan_sees_a_family_on_each_side():
    assert "odoo_up" in _rendered_families()
    assert "odoo_up" in _documented_families()
