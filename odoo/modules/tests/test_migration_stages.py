import logging
import typing
from pathlib import Path

import pytest

import odoo.modules.migration as migration_mod
from odoo.modules.migration import (
    MIGRATION_STAGES,
    MigrationManager,
    _get_scripts_by_version,
    _warn_unstaged_scripts,
)

if typing.TYPE_CHECKING:
    from odoo.db import Cursor
    from odoo.modules.module_graph import ModuleGraph


@pytest.fixture
def version_dir(tmp_path):
    d = tmp_path / "19.0.1.0"
    d.mkdir()
    return d


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


class TestUnstagedScriptsWarn:
    @pytest.mark.parametrize(
        "name",
        [
            "pre_01_typo.py",
            "Pre-01.py",
            "migrate.py",
            "0-first.py",
        ],
    )
    def test_a_script_matching_no_stage_is_reported(self, version_dir, caplog, name):
        (version_dir / name).touch()
        with caplog.at_level(logging.WARNING):
            _warn_unstaged_scripts(version_dir, [str(version_dir / name)])
        messages = _warnings(caplog)
        assert len(messages) == 1, messages
        assert name in messages[0]
        assert "never run" in messages[0]

    @pytest.mark.parametrize("stage", MIGRATION_STAGES)
    def test_a_correctly_staged_script_is_silent(self, version_dir, caplog, stage):
        path = version_dir / f"{stage}-01-thing.py"
        path.touch()
        with caplog.at_level(logging.WARNING):
            _warn_unstaged_scripts(version_dir, [str(path)])
        assert _warnings(caplog) == []

    def test_dunder_init_is_not_a_migration_script(self, version_dir, caplog):
        path = version_dir / "__init__.py"
        path.touch()
        with caplog.at_level(logging.WARNING):
            _warn_unstaged_scripts(version_dir, [str(path)])
        assert _warnings(caplog) == []


class TestCollectionWiresTheWarning:
    def test_get_scripts_by_version_reports_while_collecting(self, tmp_path, caplog):
        version_dir = tmp_path / "19.0.1.0"
        version_dir.mkdir()
        (version_dir / "pre-01-good.py").touch()
        (version_dir / "post_02_bad.py").touch()

        with caplog.at_level(logging.WARNING):
            found = _get_scripts_by_version(str(tmp_path))

        assert sorted(p.rsplit("/", 1)[-1] for p in found["19.0.1.0"]) == [
            "post_02_bad.py",
            "pre-01-good.py",
        ], "collection itself must be unchanged — this only reports"
        messages = _warnings(caplog)
        assert len(messages) == 1, messages
        assert "post_02_bad.py" in messages[0]

    def test_an_empty_path_collects_nothing_and_says_nothing(self, caplog):
        with caplog.at_level(logging.WARNING):
            assert _get_scripts_by_version("") == {}
        assert _warnings(caplog) == []


class TestStagesAreDeclaredOnce:
    def test_the_stage_tuple_is_what_migrate_module_accepts(self):
        assert MIGRATION_STAGES == ("pre", "post", "end")


class TestNonPythonScriptWarns:
    def test_a_non_py_script_is_skipped_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            migration_mod.run_migration_script(
                typing.cast("Cursor", None), "19.0.1.0", "scripts/fix.sql", "m", "pre"
            )
        messages = _warnings(caplog)
        assert len(messages) == 1, messages
        assert "fix.sql" in messages[0]
        assert "not a .py file" in messages[0]


class _FakePkg:
    def __init__(self, name, load_state):
        self.name = name
        self.load_state = load_state


def _no_cursor() -> Cursor:
    return typing.cast("Cursor", None)


def _as_graph(packages: list[_FakePkg]) -> ModuleGraph:
    return typing.cast("ModuleGraph", packages)


class TestMigrationManagerDoesNotReindexDonePackages:
    def test_indexing_skips_a_package_already_indexed(self, monkeypatch):
        calls = []
        original = migration_mod._get_scripts_by_version

        def counting(path):
            calls.append(path)
            return original(path)

        monkeypatch.setattr(migration_mod, "_get_scripts_by_version", counting)

        graph = [_FakePkg("odoo_probe_nonexistent_module", "to upgrade")]
        manager = MigrationManager(_no_cursor(), _as_graph(graph))
        assert calls, "the first index must scan the (absent) package"
        calls_after_init = len(calls)

        manager.index_migration_scripts()
        assert len(calls) == calls_after_init, (
            "index_migration_scripts() re-scanned a package already present in self.migrations"
        )

    def test_indexing_indexes_a_package_added_after_init(self, monkeypatch):
        calls = []
        original = migration_mod._get_scripts_by_version

        def counting(path):
            calls.append(path)
            return original(path)

        monkeypatch.setattr(migration_mod, "_get_scripts_by_version", counting)

        graph = [_FakePkg("odoo_probe_nonexistent_module_a", "to upgrade")]
        manager = MigrationManager(_no_cursor(), _as_graph(graph))
        calls_after_init = len(calls)

        graph.append(_FakePkg("odoo_probe_nonexistent_module_b", "to upgrade"))
        manager.index_migration_scripts()
        assert len(calls) > calls_after_init, (
            "index_migration_scripts() must still index a package newly added to the graph"
        )
        assert set(manager.migrations) == {
            "odoo_probe_nonexistent_module_a",
            "odoo_probe_nonexistent_module_b",
        }


class TestNoScriptIsSilentlySkipped:
    @staticmethod
    def _scripts():
        root = Path(__file__).resolve().parents[3]
        return [
            path
            for tree in ("odoo/addons", "addons")
            for subdir in ("migrations", "upgrades")
            for path in (root / tree).rglob(f"{subdir}/*/*.py")
            if path.name != "__init__.py"
        ]

    def test_the_glob_still_finds_scripts(self):
        assert self._scripts(), "no migration scripts found — the glob has rotted"

    def test_none_of_them_is_skipped(self):
        unstaged = sorted(
            str(p.name)
            for p in self._scripts()
            if not p.name.startswith(tuple(f"{s}-" for s in MIGRATION_STAGES))
        )
        assert unstaged == [], (
            f"{len(unstaged)} migration script(s) match no stage and will never "
            f"run: {unstaged}"
        )
