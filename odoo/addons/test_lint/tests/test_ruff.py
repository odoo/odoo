"""Integration lint tests: custom AST checkers for Odoo-specific rules.

Replaces the former ``test_pylint.py`` which shelled out to pylint with custom
astroid-based plugins.  All custom rules are now checked in-process via stdlib
``ast``.  Standard lint rules (formerly 6 pylint builtins) are delegated to
ruff via ``core/ruff.toml`` and enforced in CI — not here.
"""

import ast
import logging
import re
from pathlib import Path

from odoo import tools
from odoo.tools.misc import file_open

from . import _checker_gettext, _checker_sql, _checker_unlink, lint_case

_logger = logging.getLogger(__name__)

# Regex to parse ``# pylint: disable=rule1,rule2`` inline comments.
_PYLINT_DISABLE_RE = re.compile(r"#\s*pylint:\s*disable=([^\n]+)")

# Map our checker rule names to all known pylint message IDs so we recognise
# both ``# pylint: disable=missing-gettext`` and ``# pylint: disable=E8505``.
_RULE_ALIASES: dict[str, frozenset[str]] = {
    "sql-injection": frozenset({"sql-injection", "E8501"}),
    "gettext-variable": frozenset({"gettext-variable", "E8502"}),
    "gettext-placeholders": frozenset({"gettext-placeholders", "E8503"}),
    "gettext-repr": frozenset({"gettext-repr", "E8504"}),
    "missing-gettext": frozenset({"missing-gettext", "E8505"}),
    "raise-unlink-override": frozenset({"raise-unlink-override", "E8506"}),
}


def _is_core_path(path: str) -> bool:
    """Return True if *path* is under the core Odoo directory tree.

    Excludes addons_custom, enterprise, and other external addon directories
    to focus integration tests on standard Odoo code.
    """
    root = tools.config.root_path  # .../core/odoo
    core_dir = str(Path(root).parent)  # .../core
    return path.startswith(core_dir)


def _is_suppressed(source: bytes | str, lineno: int, rule: str) -> bool:
    """Return True if *lineno* has a ``# pylint: disable=`` covering *rule*.

    Also respects bare ``# noqa`` (suppress all) and ``# noqa: <code>`` when
    the code matches a known alias.
    """
    lines = (source if isinstance(source, bytes) else source.encode()).split(b"\n")
    if lineno < 1 or lineno > len(lines):
        return False
    line = lines[lineno - 1].decode(errors="replace")

    # Check pylint disable comment
    if m := _PYLINT_DISABLE_RE.search(line):
        disabled = {tok.strip() for tok in m.group(1).split(",")}
        aliases = _RULE_ALIASES.get(rule, frozenset({rule}))
        if disabled & aliases:
            return True

    # Check noqa (bare = suppress everything, with code = match aliases)
    if "# noqa" in line:
        noqa_idx = line.index("# noqa")
        rest = line[noqa_idx + 6 :].strip()
        if not rest or rest.startswith("  "):
            return True  # bare
        if rest.startswith(":"):
            codes = {c.strip() for c in rest[1:].split(",")}
            aliases = _RULE_ALIASES.get(rule, frozenset({rule}))
            if codes & aliases:
                return True

    return False


class TestRuff(lint_case.LintCase):
    """Run custom AST checkers on core Odoo modules."""

    def _iter_core_python_files(self):
        """Yield paths of core module Python files (excluding upgrades/migrations)."""
        for path in self.iter_module_files("*.py"):
            if not _is_core_path(path):
                continue
            # Skip upgrade/migration scripts — they use intentional dynamic SQL
            if "/upgrades/" in path or "/migrations/" in path:
                continue
            yield path

    def test_sql_injection(self):
        """Run SQL injection checker on core module Python files."""
        violations = []
        for path in self._iter_core_python_files():
            try:
                with file_open(path, "rb") as f:
                    source = f.read()
                tree = ast.parse(source, path)
            except SyntaxError:
                continue
            _checker_sql.annotate_parents(tree)
            checker = _checker_sql.SqlInjectionChecker(path)
            violations.extend((path, v) for v in checker.check(tree) if not _is_suppressed(source, v.lineno, "sql-injection"))

        if violations:
            violations.sort(key=lambda t: t[0])
            msg = "SQL injection risks detected:\n" + "\n".join(
                f"- {path}:{v.lineno}" for path, v in violations
            )
            self.fail(msg)

    def test_gettext(self):
        """Run gettext checker on core module Python files."""
        violations = []
        for path in self._iter_core_python_files():
            try:
                with file_open(path, "rb") as f:
                    source = f.read()
                tree = ast.parse(source, path)
            except SyntaxError:
                continue
            violations.extend((path, v) for v in _checker_gettext.check(tree, path) if not _is_suppressed(source, v.lineno, v.rule))

        if violations:
            violations.sort(key=lambda t: t[0])
            msg = "gettext violations detected:\n" + "\n".join(
                f"- {path}:{v.lineno} [{v.rule}] {v.message}" for path, v in violations
            )
            self.fail(msg)

    def test_unlink_override(self):
        """Run unlink override checker on core module Python files."""
        violations = []
        for path in self._iter_core_python_files():
            try:
                with file_open(path, "rb") as f:
                    source = f.read()
                tree = ast.parse(source, path)
            except SyntaxError:
                continue
            violations.extend((path, v) for v in _checker_unlink.check(tree) if not _is_suppressed(source, v.lineno, "raise-unlink-override"))

        if violations:
            violations.sort(key=lambda t: t[0])
            msg = "raise inside unlink override:\n" + "\n".join(
                f"- {path}:{v.lineno}" for path, v in violations
            )
            self.fail(msg)
