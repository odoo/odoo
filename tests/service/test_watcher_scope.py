from pathlib import Path
from unittest.mock import patch

import pytest

from odoo.service import _watcher
from odoo.service import settings as server_settings


def _tree(root):
    for rel in (
        "mod/__init__.py",
        "mod/models/a.py",
        "mod/views/v.xml",
        "mod/data/d.xml",
        "mod/security/ir.model.access.csv",
        "mod/static/src/x.js",
        "mod/wizard/sub/w.py",
        "mod/i18n/es.po",
        "theme/__manifest__.py",
        "theme/views/t.xml",
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    (root / "empty" / "deeper").mkdir(parents=True)
    return root


def _rel(root, paths):
    return sorted(str(p).removeprefix(str(root)).lstrip("/") or "." for p in paths)


class TestReloadWatchesOnlyPythonBearingSubtrees:
    """Every watch is an inotify slot from a budget the whole box shares."""

    def test_directories_without_python_below_them_are_not_watched(self, tmp_path):
        root = _tree(tmp_path)
        with server_settings.override(dev_mode=("reload",)):
            watched = _rel(root, _watcher.iter_python_watch_dirs(root))
        assert watched == [
            ".",
            "mod",
            "mod/models",
            "mod/wizard",
            "mod/wizard/sub",
            "theme",
        ]

    def test_the_root_is_watched_even_when_it_holds_no_python(self, tmp_path):
        (tmp_path / "views").mkdir()
        with server_settings.override(dev_mode=("reload",)):
            assert _rel(tmp_path, _watcher.iter_python_watch_dirs(tmp_path)) == ["."]

    def test_every_python_bearing_directory_of_the_full_walk_is_kept(self, tmp_path):
        root = _tree(tmp_path)
        with server_settings.override(dev_mode=("reload",)):
            full = set(_watcher.iter_watch_dirs(root))
            narrowed = set(_watcher.iter_python_watch_dirs(root))
        assert narrowed <= full
        dropped = full - narrowed
        assert dropped and not any(list(Path(d).glob("*.py")) for d in dropped)

    def _watcher(self, dev_mode):
        with (
            server_settings.override(dev_mode=dev_mode),
            patch.object(_watcher.FSWatcherBase, "get_watch_paths", staticmethod(list)),
            patch.object(_watcher.FSWatcherInotify, "_arm_watcher"),
        ):
            return _watcher.FSWatcherInotify()

    def test_the_assets_mode_keeps_the_full_walk(self, tmp_path):
        root = _tree(tmp_path)
        watcher = self._watcher(("reload", "assets"))
        assert watcher._python_only is False
        with server_settings.override(dev_mode=("reload", "assets")):
            assets = set(watcher._iter_root(str(root)))
            full = set(_watcher.iter_watch_dirs(root))
        assert assets == full
        assert any(d.endswith("/static/src") for d in assets)

    def test_the_reload_mode_narrows_the_walk(self, tmp_path):
        root = _tree(tmp_path)
        watcher = self._watcher(("reload",))
        assert watcher._python_only is True
        with server_settings.override(dev_mode=("reload",)):
            reload = set(watcher._iter_root(str(root)))
            narrowed = set(_watcher.iter_python_watch_dirs(root))
        assert reload == narrowed


@pytest.mark.parametrize("mode", [("reload",), ("reload", "assets")])
def test_an_unreadable_directory_is_skipped_not_fatal(tmp_path, mode):
    (tmp_path / "mod").mkdir()
    (tmp_path / "mod" / "a.py").write_text("")
    with (
        server_settings.override(dev_mode=mode),
        patch.object(_watcher.os, "scandir", side_effect=OSError("denied")),
    ):
        assert list(_watcher.iter_python_watch_dirs(tmp_path)) == [str(tmp_path)]
