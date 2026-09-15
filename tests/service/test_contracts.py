import os
import pathlib
import selectors
import signal
import subprocess
import sys
import threading
import time

import psycopg
import pytest

from odoo.db import PoolError
from odoo.service import common


class TestPsycopgConnectFailureHierarchy:
    def test_invalid_catalog_name_is_not_an_operational_error(self):
        assert not issubclass(
            psycopg.errors.InvalidCatalogName, psycopg.OperationalError
        ), (
            "InvalidCatalogName is now an OperationalError. If psycopg really "
            "changed this, odoo.service.common's comments about WHY the catch "
            "is the broad psycopg.Error tree are stale and should be revisited."
        )

    def test_invalid_catalog_name_is_a_psycopg_error(self):
        assert issubclass(psycopg.errors.InvalidCatalogName, psycopg.Error)

    @pytest.mark.parametrize(
        "arm", ["OperationalError", "ProgrammingError", "IntegrityError", "DataError"]
    )
    def test_psycopg_error_is_the_common_root(self, arm):
        assert issubclass(
            getattr(psycopg, arm, None) or getattr(psycopg.errors, arm), psycopg.Error
        )

    def test_pool_error_is_not_a_psycopg_error(self):
        assert not issubclass(PoolError, psycopg.Error)

    def test_every_expected_connect_failure_is_actually_caught(self):
        for cls in common._EXPECTED_CONNECT_FAILURES:
            assert issubclass(cls, (psycopg.Error, PoolError)), (
                f"{cls.__name__} is treated as a routine connect failure but is "
                f"not caught by exp_authenticate's except clause"
            )


class TestSubprocessPipeOwnership:
    def _run(self):
        return subprocess.Popen(
            [sys.executable, "-c", "import sys; sys.stdout.write('x')"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_popen_does_not_close_its_pipes_on_wait(self):
        proc = self._run()
        proc.wait()
        try:
            assert not proc.stdout.closed, "Popen.wait() now closes stdout"
            assert not proc.stderr.closed, "Popen.wait() now closes stderr"
        finally:
            proc.stdout.close()
            proc.stderr.close()

    def test_a_held_traceback_keeps_the_pipes_alive(self):
        holder = {}

        def boom():
            proc = self._run()
            proc.wait()
            raise RuntimeError("failure path")

        try:
            boom()
        except RuntimeError as exc:
            holder["exc"] = exc

        frame = holder["exc"].__traceback__.tb_next.tb_frame
        proc = frame.f_locals["proc"]
        try:
            assert not proc.stdout.closed, (
                "a held traceback no longer keeps the frame's Popen alive; the "
                "fd-retention rationale in _run_pg_dump is stale"
            )
        finally:
            proc.stdout.close()
            proc.stderr.close()


class TestSignalsDoNotSurfaceAsEINTR:
    def _drain(self, fd):
        while True:
            try:
                if not os.read(fd, 4096):
                    return
            except BlockingIOError:
                return

    def test_select_read_and_sleep_survive_a_signal_storm(self):
        handled = 0

        def handler(*_args):
            nonlocal handled
            handled += 1

        previous = signal.signal(signal.SIGUSR1, handler)
        read_fd, write_fd = os.pipe()
        os.set_blocking(read_fd, False)
        selector = selectors.DefaultSelector()
        selector.register(read_fd, selectors.EVENT_READ)
        target = os.getpid()
        stop = threading.Event()

        def bombard():
            for _ in range(20):
                if stop.wait(0.02):
                    return
                os.kill(target, signal.SIGUSR1)

        sender = threading.Thread(target=bombard, daemon=True)
        sender.start()
        try:
            for _ in range(20):
                selector.select(0.2)
                self._drain(read_fd)
                time.sleep(0.01)
        finally:
            stop.set()
            sender.join(timeout=2)
            selector.close()
            os.close(read_fd)
            os.close(write_fd)
            signal.signal(signal.SIGUSR1, previous)

        assert handled, "no signal was delivered; the test proved nothing"

    def test_an_argless_oserror_has_no_args_but_does_have_errno(self):
        with pytest.raises(IndexError):
            OSError().args[0]
        assert OSError().errno is None


class TestInotifyIsTheForksOwn:
    """The third-party `inotify` package used to be reached into by name-mangled
    attribute (`_Inotify__watches_r`, `_Inotify__inotify_fd`, `_Inotify__epoll`)
    from two subclasses that existed to close the descriptors it leaked."""

    def test_the_watcher_imports_no_third_party_inotify(self):
        from odoo.service import _watcher

        source = pathlib.Path(_watcher.__file__).read_text(encoding="utf-8")
        assert "from odoo.libs import inotify" in source
        for spelling in ("import inotify\n", "from inotify", "_Inotify__"):
            assert spelling not in source, spelling

    def test_the_library_owns_both_descriptors(self, tmp_path):
        from odoo.libs import inotify

        if not inotify.AVAILABLE:
            pytest.skip("inotify is a Linux facility")
        ino = inotify.Inotify()
        fds = ino.descriptors()
        assert len(fds) == 2
        ino.close()
        for fd in fds:
            with pytest.raises(OSError):
                os.fstat(fd)
