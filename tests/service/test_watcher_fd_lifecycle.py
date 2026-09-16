import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from odoo.service import _watcher

pytestmark = pytest.mark.skipif(
    not _watcher.inotify, reason="the inotify backend is not installed"
)


def _inotify_fds():
    out = []
    for entry in Path("/proc/self/fd").iterdir():
        try:
            if entry.readlink().name == "anon_inode:inotify":
                out.append(int(entry.name))
        except OSError:
            pass
    return sorted(out)


def _make_watcher(tmp_path, monkeypatch):
    root = tmp_path / "addons"
    (root / "mod" / "static").mkdir(parents=True)
    # Only a subtree that holds Python is armed; the root and `mod` make two.
    (root / "mod" / "__init__.py").write_text("")
    monkeypatch.setattr(
        _watcher.FSWatcherBase, "get_watch_paths", staticmethod(lambda: [str(root)])
    )
    return _watcher.FSWatcherInotify()


class TestInotifyDescriptorLifecycle:
    def test_stop_closes_even_when_a_tree_reference_survives(
        self, tmp_path, monkeypatch
    ):
        before = _inotify_fds()
        watcher = _make_watcher(tmp_path, monkeypatch)
        retained_tree = watcher.watcher
        descriptors = watcher.watcher.descriptors()
        watcher.stop()
        assert _inotify_fds() == before
        for fd in descriptors:
            with pytest.raises(OSError):
                os.fstat(fd)
        # Repeated closure must not close a descriptor reused by another owner.
        with Path(os.devnull).open("rb") as other:
            retained_tree.close()
            assert os.fstat(other.fileno())

    def test_failed_construction_closes_descriptors_before_traceback_dies(
        self, tmp_path, monkeypatch
    ):
        from odoo.libs import inotify

        before = _inotify_fds()
        descriptors = []
        armed = []
        real_add_watch = inotify.Inotify.add_watch

        def fail_after_arming(self, path, mask):
            wd = real_add_watch(self, path, mask)
            armed.append(wd)
            descriptors.extend(self.descriptors())
            if len(armed) == 2:
                raise RuntimeError("failure after allocating watches")
            return wd

        monkeypatch.setattr(inotify.Inotify, "add_watch", fail_after_arming)
        with pytest.raises(RuntimeError, match="failure after allocating") as retained:
            _make_watcher(tmp_path, monkeypatch)
        assert retained.value.__traceback__ is not None
        assert _inotify_fds() == before
        assert descriptors
        for fd in descriptors:
            with pytest.raises(OSError):
                os.fstat(fd)

    def test_stop_releases_the_inotify_descriptor(self, tmp_path, monkeypatch):
        before = _inotify_fds()
        watcher = _make_watcher(tmp_path, monkeypatch)
        opened = [fd for fd in _inotify_fds() if fd not in before]
        assert opened, "constructing the watcher opened no inotify descriptor"

        watcher.start()
        watcher.stop()

        assert _inotify_fds() == before, (
            "stop() left an inotify descriptor open; a --dev=reload cycle leaks "
            "one instance and every watch under it"
        )

    def test_stop_drops_every_reference_to_the_tree(self, tmp_path, monkeypatch):
        watcher = _make_watcher(tmp_path, monkeypatch)
        watcher.start()
        watcher.stop()
        assert watcher.watcher is None

    def test_the_descriptors_carry_cloexec(self, tmp_path, monkeypatch):
        watcher = _make_watcher(tmp_path, monkeypatch)
        try:
            fds = watcher.watcher.descriptors()
            assert fds
            for fd in fds:
                assert os.get_inheritable(fd) is False, (
                    f"fd {fd} is inheritable, so os.execve() in lifecycle._reexec_server "
                    f"hands it to the reloaded process"
                )
        finally:
            watcher.stop()


class TestReloadDoesNotAccumulateDescriptors:
    def test_four_reload_generations_leak_nothing(self, tmp_path):
        """One start()/stop() then execve, four times over, is --dev=reload."""
        script = tmp_path / "gen.py"
        script.write_text(
            textwrap.dedent(
                f"""
                import os, sys
                sys.path.insert(0, {str(Path(_watcher.__file__).parents[2])!r})
                gen = int(sys.argv[1])
                from odoo.service import _watcher

                root = {str(tmp_path / "addons")!r}
                _watcher.FSWatcherBase.get_watch_paths = staticmethod(lambda: [root])

                def fds():
                    out = []
                    for name in os.listdir('/proc/self/fd'):
                        try:
                            if os.readlink(f'/proc/self/fd/{{name}}') == 'anon_inode:inotify':
                                out.append(int(name))
                        except OSError:
                            pass
                    return sorted(out)

                inherited = fds()
                w = _watcher.FSWatcherInotify()
                w.start()
                w.stop()
                print(f'gen {{gen}} inherited {{inherited}}', flush=True)
                if gen < 4:
                    os.execve(sys.executable, [sys.executable, __file__, str(gen + 1)], os.environ)
                """
            )
        )
        (tmp_path / "addons" / "mod" / "static").mkdir(parents=True)
        proc = subprocess.run(
            [sys.executable, str(script), "1"],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        lines = [l for l in proc.stdout.splitlines() if l.startswith("gen ")]
        assert len(lines) == 4, proc.stdout
        for line in lines:
            assert line.endswith("inherited []"), (
                f"a reload generation inherited leaked inotify descriptors: {line!r}\n"
                f"{proc.stdout}"
            )


def _watched_paths(watcher):
    return set(watcher.watcher.watched)


class TestOnlyDirectoriesThatCanChangeAreWatched:
    """A --dev=reload server asked for ~25k watches over the five addon roots,
    ~15k of them __pycache__ (which reports its own .pyc writes), .git, i18n
    and static; a box's watch budget is shared with every editor on it."""

    @pytest.fixture
    def tree(self, tmp_path):
        root = tmp_path / "addons"
        for name in (
            "mod/models",
            "mod/models/__pycache__",
            "mod/static/src",
            "mod/i18n",
            "mod/.git/objects",
            "mod/static/lib/node_modules/x",
            "mod/tests",
            "mod/views",
        ):
            (root / name).mkdir(parents=True)
        for name in ("mod/__init__.py", "mod/models/a.py", "mod/tests/test_a.py"):
            (root / name).write_text("")
        (root / "mod/views/v.xml").write_text("")
        return root

    def _arm(self, tree, monkeypatch, dev_mode):
        from odoo.service import settings as server_settings

        monkeypatch.setattr(
            _watcher.FSWatcherBase,
            "get_watch_paths",
            staticmethod(lambda: [str(tree)]),
        )
        with server_settings.override(dev_mode=dev_mode, workers=0):
            watcher = _watcher.FSWatcherInotify()
            try:
                return {
                    Path(p).relative_to(tree).as_posix()
                    for p in _watched_paths(watcher)
                }
            finally:
                watcher._release_watcher()

    def test_reload_alone_skips_static_pycache_git_i18n_and_views(
        self, tree, monkeypatch
    ):
        assert self._arm(tree, monkeypatch, ("reload",)) == {
            ".",
            "mod",
            "mod/models",
            "mod/tests",
        }

    def test_assets_keeps_static_but_not_its_node_modules(self, tree, monkeypatch):
        watched = self._arm(tree, monkeypatch, ("reload", "assets"))
        assert "mod/static/src" in watched
        assert "mod/static/lib" in watched
        assert "mod/static/lib/node_modules" not in watched
        assert "mod/models/__pycache__" not in watched
        assert "mod/views" in watched
