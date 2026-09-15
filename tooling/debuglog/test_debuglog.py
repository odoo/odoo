import textwrap
from pathlib import Path

import pytest

from . import debuglog

CLEAN = textwrap.dedent(
    """
    import logging

    _logger = logging.getLogger(__name__)


    def work(records, cr):
        total = 0
        for record in records:
            total += record
        if total > 10:
            cr.execute("SELECT 1")
        return total


    def audit(records):
        return len(records)
    """
).lstrip()

INSTRUMENTED = textwrap.dedent(
    """
    import logging

    from odoo.libs.debug_log import DebugLog

    _logger = logging.getLogger(__name__)
    _debug = DebugLog(__name__)


    def work(records, cr):
        total = 0
        seen = 0  # debuglog
        with _debug.perf("work", cr=cr, records=len(records)) as span:
            for record in records:
                total += record
                seen += 1  # debuglog
            span.set(total=total)
        if _debug.logic.enabled and total > 10:
            _debug.logic("work.large", total=total)
        if total > 10:
            _debug.pipeline("work.execute", total=total)
            cr.execute("SELECT 1")
        _debug.perf.count("work.done", total=total)
        _debug.lifecycle("work.end")
        return total


    @_debug.perf.timed
    def audit(records):
        return len(records)
    """
).lstrip()


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source)
    return path


def _check(tmp_path: Path, source: str) -> list[str]:
    path = _write(tmp_path, "mod.py", source)
    report = debuglog.scan_file(path)
    assert report is not None
    return [v.message for v in report.violations]


def test_every_documented_shape_passes_check(tmp_path):
    assert _check(tmp_path, INSTRUMENTED) == []


def test_strip_restores_the_clean_module(tmp_path):
    path = _write(tmp_path, "mod.py", INSTRUMENTED)
    report = debuglog.scan_file(path)
    assert report is not None
    stripped = debuglog.strip_file(report)
    assert stripped.split() == CLEAN.split()
    assert not debuglog._SURVIVOR_RE.search(stripped)


def test_list_counts_one_site_per_channel_kind(tmp_path):
    path = _write(tmp_path, "mod.py", INSTRUMENTED)
    report = debuglog.scan_file(path)
    assert report is not None
    kinds = sorted(site.kind for site in report.sites)
    assert kinds == sorted(
        [
            "import",
            "assignment",
            "decorator",
            "span",
            "span_set",
            "guard",
            "line",
            "line",
            "line",
            "marker",
            "marker",
        ]
    )


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ("    _debug.perf('x')\n", "bare _debug.perf"),
        (
            "    with _debug.perf('x'), open('f') as f:\n        pass\n",
            "only item",
        ),
        (
            "    if _debug.logic.enabled:\n        pass\n    else:\n        pass\n",
            "no else",
        ),
        ("    if flag:\n        _debug.logic('x')\n", "only statement"),
        ("    value = _debug.perf('x')\n", "outside the strippable shapes"),
        ("    other = DebugLog('x')\n", "module-level"),
        ("    if _debug.logic.enabled:\n        total = 1\n", "debug lines and"),
        (
            "    _debug.logic('x', a=1, **{'b': 2})\n    return 1\n",
            "may not mix explicit keywords",
        ),
        (
            "    with _debug.perf('x', a=1, **{'b': 2}):\n        pass\n",
            "may not mix explicit keywords",
        ),
        ("    _debug.logic(*parts)\n", "may not use a `*` expansion"),
        (
            "    with _debug.perf(*parts):\n        pass\n",
            "may not use a `*` expansion",
        ),
    ],
)
def test_check_refuses_an_unstrippable_shape(tmp_path, body, fragment):
    source = (
        "from odoo.libs.debug_log import DebugLog\n"
        "_debug = DebugLog(__name__)\n"
        "flag = True\n"
        "parts = ['x']\n"
        "def f():\n" + body + "    return 1\n"
    )
    messages = _check(tmp_path, source)
    assert any(fragment in message for message in messages), messages


def test_the_timed_decorator_is_a_perf_site(tmp_path):
    """`@_debug.perf.timed` is a recognised shape, counted on the perf channel.

    It was refused until 2026-09-15, which left 1,350 sites -- 1,346 of them in
    `account` -- in a shape the strip pass could not remove. Nobody noticed
    because this checker had been deleted with `odoo/tooling/` and had to be
    recovered from history before it could run at all.
    """
    source = (
        "from odoo.libs.debug_log import DebugLog\n"
        "_debug = DebugLog(__name__)\n"
        "class C:\n"
        "    @_debug.perf.timed\n"
        "    def f(self):\n"
        "        return 1\n"
    )
    path = _write(tmp_path, "mod.py", source)
    report = debuglog.scan_file(path)
    assert report is not None
    assert [v.message for v in report.violations] == []
    decorators = [site for site in report.sites if site.kind == "decorator"]
    assert len(decorators) == 1
    assert decorators[0].channel == "perf"
    assert decorators[0].line == decorators[0].end == 4


def test_stripping_the_timed_decorator_leaves_the_method(tmp_path):
    source = (
        "from odoo.libs.debug_log import DebugLog\n"
        "_debug = DebugLog(__name__)\n"
        "class C:\n"
        "    @property\n"
        "    @_debug.perf.timed\n"
        "    def f(self):\n"
        "        return 1\n"
    )
    path = _write(tmp_path, "mod.py", source)
    report = debuglog.scan_file(path)
    assert report is not None
    stripped = debuglog.strip_file(report)
    assert "_debug.perf.timed" not in stripped
    # the method and every decorator that is not ours survive untouched
    assert "@property" in stripped
    assert "def f(self):" in stripped
    assert "return 1" in stripped
    assert not debuglog._SURVIVOR_RE.search(stripped)


def test_the_timed_decorator_is_refused_when_called(tmp_path):
    """Only the bare form is a shape: `timed` takes the function itself."""
    source = (
        "from odoo.libs.debug_log import DebugLog\n"
        "_debug = DebugLog(__name__)\n"
        "def f():\n"
        "    return 1\n"
    ).replace("def f():", "@_debug.perf.timed()\ndef f():")
    messages = _check(tmp_path, source)
    assert any("outside the strippable shapes" in m for m in messages), messages


def test_a_splat_without_explicit_keywords_is_allowed(tmp_path):
    """`event` is positional-only, so a lone `**` expansion cannot collide."""
    source = (
        "from odoo.libs.debug_log import DebugLog\n"
        "_debug = DebugLog(__name__)\n"
        "def f(counts):\n"
        "    _debug.pipeline('x', **counts)\n"
        "    return 1\n"
    )
    assert _check(tmp_path, source) == []


def test_a_positional_star_is_refused_even_where_it_would_work_today(tmp_path):
    """A one-element sequence binds `event` and passes; two raise.

    So the shape is green until the sequence grows, which is why it is refused
    on its form rather than on a length the checker cannot know.
    """
    source = (
        "from odoo.libs.debug_log import DebugLog\n"
        "_debug = DebugLog(__name__)\n"
        "def f():\n"
        "    _debug.lifecycle(*['x'])\n"
        "    return 1\n"
    )
    messages = _check(tmp_path, source)
    assert any("may not use a `*` expansion" in m for m in messages), messages


def test_a_module_without_debug_references_is_skipped(tmp_path):
    path = _write(tmp_path, "mod.py", CLEAN)
    assert debuglog.scan_file(path) is None


def test_the_core_tree_passes_check():
    roots = [debuglog.REPO / "odoo" / d for d in ("orm", "db", "http", "service")]
    reports = debuglog.scan(roots)
    violations = [v for report in reports for v in report.violations]
    assert violations == []


def test_a_test_suite_is_skipped_but_a_package_named_tests_is_scanned(tmp_path):
    suite = tmp_path / "addon" / "tests"
    suite.mkdir(parents=True)
    _write(suite, "test_thing.py", INSTRUMENTED)
    _write(suite, "helper.py", INSTRUMENTED)
    framework = tmp_path / "odoo" / "tests"
    framework.mkdir(parents=True)
    _write(framework, "loader.py", INSTRUMENTED)
    _write(tmp_path, "conftest.py", INSTRUMENTED)
    scanned = {
        path.relative_to(tmp_path).as_posix()
        for path in debuglog.iter_files([tmp_path])
    }
    assert scanned == {"odoo/tests/loader.py"}
