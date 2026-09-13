import ast
import functools
import re

from .._pg import repo_root
from .conftest import patch_target_sources

ROOT = repo_root()
PKG = ROOT / "odoo" / "service" / "db"
SUBMODULES = frozenset(p.stem for p in PKG.glob("*.py") if p.stem != "__init__")

_STRING_TARGET = re.compile(r'["\']odoo\.service\.db\.([A-Za-z_][\w.]*)["\']')

_ALIAS_BINDING = re.compile(
    r"^\s*(?:import\s+odoo\.service\.db\s+as\s+(\w+)"
    r"|from\s+odoo\.service\s+import\s+db(?:\s+as\s+(\w+))?)",
    re.MULTILINE,
)

_FIXTURE_BINDING = re.compile(
    r"^def\s+(\w+)\([^)]*\):(?:(?!\n(?:def|class)\s).)*?"
    r"import\s+odoo\.service\.db\b",
    re.MULTILINE | re.DOTALL,
)


def _package_aliases(text: str) -> set[str]:
    names = {m.group(1) or m.group(2) or "db" for m in _ALIAS_BINDING.finditer(text)}
    names.update(m.group(1) for m in _FIXTURE_BINDING.finditer(text))
    return names


def _object_targets(text: str):
    for alias in _package_aliases(text):
        pattern = re.compile(
            r"(?:patch\.object|monkeypatch\.setattr)\(\s*"
            + re.escape(alias)
            + r"\s*,\s*[\"']([A-Za-z_]\w*)[\"']"
        )
        yield from pattern.finditer(text)


PACKAGE_LEVEL_OK = frozenset(
    {"check_super", "restore_db", "list_dbs", "dispatch", "dump_db"}
)


@functools.cache
def _module_uses(sub: str, name: str) -> bool:
    tree = ast.parse((PKG / f"{sub}.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return True
        elif isinstance(node, ast.Import):
            if any((a.asname or a.name).split(".")[0] == name for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if any((a.asname or a.name) == name for a in node.names):
                return True
        elif isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                return True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                return True
    return False


def test_the_package_is_a_package():
    assert SUBMODULES, "odoo/service/db/ has no submodules; the split was undone"
    assert {
        "_checks",
        "_dump_scanner",
        "dump",
        "lifecycle",
        "listing",
        "restore",
        "rpc",
    } == SUBMODULES


def test_no_string_patch_aims_at_the_package():
    bad = []
    for path, text in patch_target_sources():
        for m in _STRING_TARGET.finditer(text):
            head = m.group(1).split(".")[0]
            if head in SUBMODULES or head in PACKAGE_LEVEL_OK:
                continue
            line = text[: m.start()].count("\n") + 1
            bad.append(f"{path.relative_to(ROOT)}:{line} -> {m.group(0)}")
    assert not bad, (
        "patch target(s) aimed at the odoo.service.db package rather than the "
        "module that uses the name. The package re-exports it, so the patch "
        "binds an alias and the real call site is untouched — silently:\n  "
        + "\n  ".join(bad)
        + "\n\nUse odoo.service.db.<lifecycle|dump|restore|listing|rpc>.<name>, "
        "or add the name to PACKAGE_LEVEL_OK with the caller that justifies it."
    )


def test_no_object_patch_aims_at_the_package():
    bad = []
    for path, text in patch_target_sources():
        for m in _object_targets(text):
            if m.group(1) in PACKAGE_LEVEL_OK:
                continue
            line = text[: m.start()].count("\n") + 1
            bad.append(f"{path.relative_to(ROOT)}:{line} -> {m.group(1)}")
    assert not bad, (
        "patch.object/setattr aimed at the odoo.service.db package (under "
        "whatever name the file binds it to). The name there is a re-export, so "
        "the patch binds an alias and the real call site is untouched. Use "
        "<alias>.<submodule>:\n  " + "\n  ".join(bad)
    )


def test_every_submodule_target_is_real():
    bad = []
    for path, text in patch_target_sources():
        for m in _STRING_TARGET.finditer(text):
            parts = m.group(1).split(".")
            if parts[0] not in SUBMODULES or len(parts) < 2:
                continue
            if not _module_uses(parts[0], parts[1]):
                line = text[: m.start()].count("\n") + 1
                bad.append(f"{path.relative_to(ROOT)}:{line} -> {m.group(0)}")
        for m in re.finditer(
            r"patch\.object\(\s*db_mod\.(\w+)\s*,\s*[\"'](\w+)[\"']", text
        ):
            if m.group(1) in SUBMODULES and not _module_uses(m.group(1), m.group(2)):
                line = text[: m.start()].count("\n") + 1
                bad.append(f"{path.relative_to(ROOT)}:{line} -> {m.group(0)}")
    assert not bad, (
        "patch target(s) naming a submodule that does not bind the name — the "
        "patch would create the attribute and nothing would read it:\n  "
        + "\n  ".join(bad)
    )


def test_the_guard_would_catch_a_regression():
    assert _STRING_TARGET.search('patch("odoo.service.db._create_empty_database")')
    db_mod_fixture = (
        "def db_mod():\n    import odoo.service.db as mod\n    return mod\n"
    )
    assert list(
        _object_targets(db_mod_fixture + 'patch.object(db_mod, "drop_database")')
    )
    assert list(
        _object_targets(
            db_mod_fixture + 'monkeypatch.setattr(db_mod, "_STDERR_DRAIN_JOIN_S", 1)'
        )
    )
    assert not list(
        _object_targets(
            "def db_mod():\n"
            "    return _dump_scanner\n"
            'patch.object(db_mod, "_check_dump_sql_safe")'
        )
    )
    assert list(
        _object_targets(
            "from odoo.service import db as db_service\n"
            'patch.object(db_service, "drop_database")'
        )
    )
    assert not list(
        _object_targets(
            "from odoo.service import db as db_service\n"
            'patch.object(db_service.lifecycle, "drop_database")'
        )
    )
    assert _module_uses("lifecycle", "_create_empty_database")
    assert not _module_uses("listing", "_create_empty_database")
