import errno
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _watcher

from .conftest import requires_inotify


@pytest.fixture
def sysctl(tmp_path):
    def _write(**values):
        for name, value in values.items():
            (tmp_path / name).write_text(f"{value}\n")
        return patch.object(_watcher, "INOTIFY_SYSCTL_DIR", tmp_path)

    return _write


class TestInotifyLimitDiagnosis:
    def test_an_unrelated_error_gets_no_diagnosis(self, sysctl):
        with sysctl(max_user_instances=128, max_user_watches=65536):
            assert (
                _watcher.get_inotify_limit_diagnosis(OSError(errno.EACCES, "nope"))
                == ""
            )

    def test_an_exception_with_no_errno_gets_no_diagnosis(self, sysctl):
        with sysctl(max_user_instances=128, max_user_watches=65536):
            assert _watcher.get_inotify_limit_diagnosis(ValueError("unrelated")) == ""

    def test_enospc_names_both_limits_and_their_values(self, sysctl):
        with sysctl(max_user_instances=128, max_user_watches=65536):
            message = _watcher.get_inotify_limit_diagnosis(OSError(errno.ENOSPC, "no"))
        assert "fs.inotify.max_user_instances=128" in message
        assert "fs.inotify.max_user_watches=65536" in message
        assert "not disk space" in message, (
            "ENOSPC reads as a full filesystem to everyone who has ever seen "
            "it; the message has to say otherwise or the operator debugs the "
            "wrong thing"
        )

    def test_an_unreadable_limit_does_not_lose_the_other_one(self, sysctl):
        with sysctl(max_user_watches=65536):
            message = _watcher.get_inotify_limit_diagnosis(OSError(errno.ENOSPC, "no"))
        assert "fs.inotify.max_user_instances=unreadable" in message
        assert "fs.inotify.max_user_watches=65536" in message, (
            "a diagnosis that raises while explaining a failure is worse than "
            "no diagnosis"
        )

    def test_it_explains_that_instances_are_shared_across_processes(self, sysctl):
        with sysctl(max_user_instances=128, max_user_watches=65536):
            message = _watcher.get_inotify_limit_diagnosis(OSError(errno.ENOSPC, "no"))
        assert "editor" in message, (
            "the usual cause is another process holding the instances, and the "
            "message is where that gets said"
        )


@requires_inotify
class TestBuildWatcher:
    def _build(self, exc, tmp_path):
        from odoo.libs import inotify

        obj = object.__new__(_watcher.FSWatcherInotify)
        obj.block_duration_s = 0.5
        with patch.object(inotify.Inotify, "add_watch", side_effect=exc):
            obj._arm_watcher([str(tmp_path)])
        return obj

    def test_an_unrecognised_failure_is_re_raised_unchanged(self, tmp_path):
        original = RuntimeError("something else entirely")
        with pytest.raises(RuntimeError) as caught:
            self._build(original, tmp_path)
        assert caught.value is original, (
            "wrapping an unrelated fault in an inotify-capacity message sends "
            "the reader after the wrong sysctl"
        )

    def test_a_capacity_failure_is_re_raised_as_enospc_with_the_diagnosis(
        self, tmp_path
    ):
        with pytest.raises(OSError) as caught:
            self._build(OSError(errno.ENOSPC, "no space"), tmp_path)
        assert caught.value.errno == errno.ENOSPC
        assert "fs.inotify" in str(caught.value)
        assert isinstance(caught.value.__cause__, OSError), (
            "the original must stay reachable as __cause__; the traceback is "
            "the only thing that says which watch it died on"
        )

    def test_a_failed_build_leaves_no_instance_behind(self, tmp_path):
        from odoo.libs import inotify

        closed = []
        real_close = inotify.Inotify.close

        def close(self):
            closed.append(self)
            real_close(self)

        with (
            patch.object(inotify.Inotify, "close", close),
            pytest.raises(RuntimeError),
        ):
            self._build(RuntimeError("boom"), tmp_path)
        assert len(closed) == 1

    def test_a_successful_build_arms_every_root(self, tmp_path):
        (tmp_path / "a" / "models").mkdir(parents=True)
        (tmp_path / "b").mkdir()
        obj = object.__new__(_watcher.FSWatcherInotify)
        obj.block_duration_s = 0.5
        obj._arm_watcher([str(tmp_path / "a"), str(tmp_path / "b")])
        try:
            assert obj.roots == [str(tmp_path / "a"), str(tmp_path / "b")]
            assert obj.watcher.watched == {
                str(tmp_path / "a"),
                str(tmp_path / "a" / "models"),
                str(tmp_path / "b"),
            }
        finally:
            obj._release_watcher()


@requires_inotify
class TestWatchDirectory:
    def _watcher_with(self, watcher):
        obj = object.__new__(_watcher.FSWatcherInotify)
        obj.watcher = watcher
        return obj

    def test_a_directory_is_armed_with_the_listen_mask(self):
        watcher = MagicMock()
        self._watcher_with(watcher)._watch_directory(Path("/tmp/x"))
        watcher.add_watch.assert_called_once_with(
            Path("/tmp/x"), _watcher.INOTIFY_LISTEN_EVENTS
        )

    def test_a_released_watcher_takes_no_watch(self):
        self._watcher_with(None)._watch_directory(Path("/tmp/x"))

    def test_an_unwatchable_directory_warns_rather_than_killing_the_watcher(
        self, caplog, sysctl
    ):
        watcher = MagicMock()
        watcher.add_watch.side_effect = OSError(errno.ENOSPC, "no space")
        with (
            sysctl(max_user_instances=128, max_user_watches=65536),
            caplog.at_level(logging.WARNING, logger="odoo.service.server"),
        ):
            self._watcher_with(watcher)._watch_directory(Path("/tmp/x"))
        message = caplog.text
        assert "cannot watch /tmp/x" in message
        assert "fs.inotify" in message, (
            "one unwatchable directory must not take the watcher down, but it "
            "must say WHY, or autoreload silently stops covering that subtree"
        )


@requires_inotify
class TestResyncAfterOverflow:
    def _sync_watches_after_overflow(self, tmp_path, roots):
        obj = object.__new__(_watcher.FSWatcherInotify)
        obj.roots = [str(r) for r in roots]
        watched, invalidated = [], []
        obj._watch_directory = lambda d: watched.append(Path(d))
        obj.on_asset_file_changed = invalidated.append
        obj._sync_watches_after_overflow()
        return watched, invalidated

    def test_every_directory_under_every_root_is_re_armed(self, tmp_path):
        root = tmp_path / "src"
        (root / "a" / "b").mkdir(parents=True)
        (root / "c").mkdir()
        watched, _ = self._sync_watches_after_overflow(tmp_path, [root])
        assert set(watched) == {root, root / "a", root / "a" / "b", root / "c"}, (
            "overflow means events were LOST, including the ones that would "
            "have armed watches on new directories; re-arming only the roots "
            "leaves every subtree created during the gap invisible"
        )

    def test_a_root_that_no_longer_exists_is_skipped_not_fatal(self, tmp_path):
        alive = tmp_path / "alive"
        alive.mkdir()
        watched, _ = self._sync_watches_after_overflow(
            tmp_path, [tmp_path / "deleted", alive]
        )
        assert set(watched) == {alive}, "the deleted root must not raise"

    def test_the_root_and_its_tree_are_armed_once_each(self, tmp_path):
        root = tmp_path / "src"
        (root / "models").mkdir(parents=True)
        (root / "__pycache__").mkdir()
        (root / "i18n").mkdir()
        watched, _ = self._sync_watches_after_overflow(tmp_path, [root])
        assert watched == [root, root / "models"], (
            "the root once, its reload-relevant subtree, nothing that can "
            "hold no reloadable source"
        )

    def test_the_asset_caches_are_dropped(self, tmp_path):
        root = tmp_path / "src"
        root.mkdir()
        _, invalidated = self._sync_watches_after_overflow(tmp_path, [root])
        assert invalidated == [_watcher.OVERFLOW_PATH], (
            "a bundle rebuilt from a file whose change event was dropped is "
            "stale until something else touches it"
        )


@requires_inotify
class TestCreatedDirectoryVanished:
    def _handle(self, created_dir):
        obj = object.__new__(_watcher.FSWatcherInotify)
        obj.watcher = MagicMock()
        obj.on_file_changed = MagicMock(return_value=None)
        event = MagicMock()
        event.name = created_dir.name
        event.full_path = str(created_dir)
        return obj, obj._handle_created_directory(event)

    def test_a_directory_gone_before_the_scan_does_not_kill_the_watcher(self, tmp_path):
        # The race: git checkout/stash, mkdtemp and editors create and remove
        # directories fast enough that the CREATE event is read after the
        # rmdir.  The scan must skip it, or the exception propagates through
        # _run() and the watcher thread dies for the rest of the session.
        obj, result = self._handle(tmp_path / "vanished")
        assert result is False
        obj.on_file_changed.assert_not_called()

    def test_a_subdirectory_gone_mid_scan_does_not_lose_its_siblings(self, tmp_path):
        created = tmp_path / "mod"
        (created / "gone").mkdir(parents=True)
        (created / "kept").mkdir()
        (created / "kept" / "models.py").write_text("")

        obj = object.__new__(_watcher.FSWatcherInotify)
        obj.watcher = MagicMock()
        seen = []
        obj.on_file_changed = lambda path: seen.append(path) and None

        real_iterdir = Path.iterdir

        def iterdir(self):
            if self == created / "gone":
                raise FileNotFoundError(errno.ENOENT, "gone", str(self))
            return real_iterdir(self)

        event = MagicMock()
        event.name = created.name
        event.full_path = str(created)
        with patch.object(Path, "iterdir", iterdir):
            assert obj._handle_created_directory(event) is False
        assert seen == [str(created / "kept" / "models.py")], (
            "one vanished subdirectory must not stop the scan of the rest of "
            "the created tree"
        )
