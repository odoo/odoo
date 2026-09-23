import os
import struct

import pytest

from odoo.libs import inotify

_HEADER = struct.Struct("iIII")


def _packed(wd, mask, name=b""):
    padded = name + b"\0" * (4 - len(name) % 4) if name else b""
    return _HEADER.pack(wd, mask, 0, len(padded)) + padded


class TestEventParsing:
    def _instance(self):
        obj = inotify.Inotify.__new__(inotify.Inotify)
        obj._fd = -1
        obj._wd_by_path = {"/w": 1}
        obj._paths_by_wd = {1: ["/w"]}
        obj._pending = b""
        return obj

    def test_events_carry_their_watch_path_and_name(self):
        obj = self._instance()
        data = _packed(1, inotify.IN_CREATE | inotify.IN_ISDIR, b"sub") + _packed(
            1, inotify.IN_MODIFY, b"a.py"
        )
        events, rest, overflowed = obj._parse(data)
        assert [(e.full_path, e.is_dir, e.is_creation) for e in events] == [
            ("/w/sub", True, True),
            ("/w/a.py", False, False),
        ]
        assert rest == b"" and overflowed is False

    def test_a_partial_trailing_record_is_kept_for_the_next_read(self):
        obj = self._instance()
        whole = _packed(1, inotify.IN_MODIFY, b"a.py")
        events, rest, _ = obj._parse(whole + whole[:7])
        assert len(events) == 1
        assert rest == whole[:7]

    def test_overflow_is_reported_and_the_batch_still_parses(self):
        obj = self._instance()
        data = _packed(-1, inotify.IN_Q_OVERFLOW) + _packed(1, inotify.IN_MODIFY, b"x")
        events, _, overflowed = obj._parse(data)
        assert overflowed is True
        assert [e.name for e in events] == ["x"]

    def test_an_ignored_watch_is_forgotten(self):
        obj = self._instance()
        obj._parse(_packed(1, inotify.IN_IGNORED))
        assert obj.watched == frozenset()

    def test_an_unknown_descriptor_is_dropped(self):
        obj = self._instance()
        events, _, _ = obj._parse(_packed(42, inotify.IN_MODIFY, b"x"))
        assert events == []


@pytest.mark.skipif(not inotify.AVAILABLE, reason="inotify is a Linux facility")
class TestAgainstTheKernel:
    def test_a_write_and_a_directory_creation_are_read_back(self, tmp_path):
        with inotify.Inotify() as ino:
            ino.add_watch(tmp_path, inotify.IN_CREATE | inotify.IN_ISDIR)
            assert all(not os.get_inheritable(fd) for fd in ino.descriptors())
            (tmp_path / "a.py").write_text("x")
            (tmp_path / "sub").mkdir()
            events = ino.read(2.0)
        assert [(e.name, e.is_dir) for e in events] == [("a.py", False), ("sub", True)]
        assert ino.closed and ino.descriptors() == ()

    def test_re_adding_a_path_returns_the_same_descriptor(self, tmp_path):
        with inotify.Inotify() as ino:
            first = ino.add_watch(tmp_path, inotify.IN_CREATE)
            assert ino.add_watch(tmp_path, inotify.IN_CREATE) == first
            assert ino.watched == {str(tmp_path)}
            assert ino.remove_watch(tmp_path) is True
            assert ino.remove_watch(tmp_path) is False

    def test_a_removed_directory_drops_its_watch_on_the_next_read(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        with inotify.Inotify() as ino:
            ino.add_watch(sub, inotify.IN_CREATE)
            sub.rmdir()
            ino.read(2.0)
            assert ino.watched == frozenset()

    def test_aliases_of_one_directory_stay_watched_until_the_last_goes(self, tmp_path):
        with inotify.Inotify() as ino:
            plain, slashed = str(tmp_path), f"{tmp_path}/"
            assert ino.add_watch(plain, inotify.IN_CREATE) == ino.add_watch(
                slashed, inotify.IN_CREATE
            )
            assert ino.remove_watch(slashed) is True
            assert ino.watched == {plain}
            (tmp_path / "f").touch()
            assert [e.name for e in ino.read(2.0)] == ["f"]
            assert ino.remove_watch(plain) is True
            assert ino.watched == frozenset()

    def test_a_replaced_directory_keeps_its_new_watch(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        with inotify.Inotify() as ino:
            old = ino.add_watch(sub, inotify.IN_CREATE)
            sub.rmdir()
            sub.mkdir()
            assert ino.add_watch(sub, inotify.IN_CREATE) != old
            ino.read(2.0)
            assert ino.watched == {str(sub)}
            (sub / "f").touch()
            assert [e.name for e in ino.read(2.0)] == ["f"]
            assert ino.remove_watch(sub) is True

    def test_an_ignored_watch_forgets_every_alias(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        with inotify.Inotify() as ino:
            ino.add_watch(sub, inotify.IN_CREATE)
            ino.add_watch(f"{sub}/", inotify.IN_CREATE)
            sub.rmdir()
            ino.read(2.0)
            assert ino.watched == frozenset()

    def test_a_failed_epoll_closes_the_inotify_descriptor(self, monkeypatch):
        opened = []
        real_init = inotify._get_libc().inotify_init1

        def init(flags):
            fd = real_init(flags)
            opened.append(fd)
            return fd

        def no_epoll():
            raise OSError(24, "Too many open files")

        monkeypatch.setattr(inotify._get_libc(), "inotify_init1", init)
        monkeypatch.setattr(inotify.select, "epoll", no_epoll)
        try:
            inotify.Inotify()
        except OSError:
            # The traceback still holds the half-built instance here, so only
            # an explicit close -- not garbage collection -- has freed the fd.
            with pytest.raises(OSError):
                os.fstat(opened[0])
        else:
            pytest.fail("the epoll failure was swallowed")

    def test_a_quiet_read_returns_after_its_timeout(self, tmp_path):
        with inotify.Inotify() as ino:
            ino.add_watch(tmp_path, inotify.IN_CREATE)
            assert ino.read(0.05) == []
