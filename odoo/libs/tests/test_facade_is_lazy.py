import subprocess
import sys
import textwrap

_HEAVY = ("lxml", "markupsafe", "arabic_reshaper")


def _modules_after(code: str) -> set[str]:
    script = textwrap.dedent(f"""
        import sys
        {code}
        print(" ".join(sorted({{m.split(".")[0] for m in sys.modules}})))
    """)
    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(out.stdout.split())


def test_importing_the_facade_does_not_pull_the_html_stack():
    loaded = _modules_after("import odoo.libs")
    heavy = sorted(set(_HEAVY) & loaded)
    assert not heavy, (
        f"`import odoo.libs` now loads {heavy}. The facade has gone eager again "
        "-- every consumer of the dependency-free layer pays for the HTML "
        "sanitiser. The package itself imports nothing; import the area."
    )


def test_importing_an_area_does_not_pull_the_html_stack():
    loaded = _modules_after("from odoo.libs.collections import Collector")
    heavy = sorted(set(_HEAVY) & loaded)
    assert not heavy, f"`from odoo.libs.collections import ...` now loads {heavy}"


def test_the_text_area_is_still_reachable_and_still_the_heavy_one():
    loaded = _modules_after("from odoo.libs.text import human_size; human_size(1)")
    assert "odoo" in loaded
    heavy_on_demand = _modules_after("import odoo.libs.text")
    assert set(_HEAVY) & heavy_on_demand, (
        "odoo.libs.text no longer imports the HTML stack, so the laziness above "
        "proves nothing -- re-measure and rewrite these tests."
    )
