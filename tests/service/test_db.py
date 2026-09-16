import contextlib
import io
import logging
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import warnings
import zipfile
from contextlib import ExitStack
from subprocess import CompletedProcess
from unittest.mock import MagicMock, call, patch

import pytest

from .conftest import fake_pg_connection, fake_pg_cursor


@pytest.fixture(scope="module")
def db_mod():
    import odoo.db.schema  # noqa: F401
    import odoo.service.db as mod

    return mod


class _MockConfig(dict):
    def filestore(self, name: str) -> str:
        return f"/nonexistent/filestore/{name}"


class _FlippingListDb(_MockConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads = 0

    def __getitem__(self, key):
        if key == "list_db":
            self.reads += 1
            return self.reads == 1
        return super().__getitem__(key)


@pytest.fixture
def bypass_db_mgmt(db_mod):
    import odoo.tools

    with patch.object(odoo.tools, "config", _MockConfig({"list_db": True})):
        yield


@pytest.fixture
def zip_dump():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("dump.sql", "-- empty sql dump\n")
        tmp = f.name
    yield tmp
    pathlib.Path(tmp).unlink()


class TestRestoreDbPreFlight:
    def test_raises_when_db_already_exists(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(
                db_mod.restore, "exp_db_exist", return_value=True
            ) as mock_exist,
            patch.object(db_mod.restore, "_create_empty_database") as mock_create,
        ):
            with pytest.raises(RuntimeError, match="already exists"):
                db_mod.restore_db("already_there", "/dev/null")

        mock_exist.assert_called_once_with("already_there")
        mock_create.assert_not_called()


class TestRestoreDbSubprocessFailure:
    def _make_patches(self, db_mod, pg_stderr: str):
        return {
            "exp_db_exist": patch.object(
                db_mod.restore, "exp_db_exist", return_value=False
            ),
            "create_empty": patch.object(db_mod.restore, "_create_empty_database"),
            "drop_database": patch.object(db_mod.lifecycle, "drop_database"),
            "subprocess_run": patch(
                "odoo.service.db.restore.subprocess.run",
                return_value=CompletedProcess(args=[], returncode=1, stderr=pg_stderr),
            ),
        }

    def test_error_message_includes_pg_stderr(self, db_mod, bypass_db_mgmt, zip_dump):
        pg_msg = 'FATAL: role "odoo" does not exist'
        patches = self._make_patches(db_mod, pg_msg)

        with (
            patches["exp_db_exist"],
            patches["create_empty"],
            patches["drop_database"],
            patches["subprocess_run"],
        ):
            with pytest.raises(RuntimeError, match="FATAL: role"):
                db_mod.restore_db("newdb", zip_dump)

    def test_empty_db_is_dropped_on_pg_failure(self, db_mod, bypass_db_mgmt, zip_dump):
        patches = self._make_patches(db_mod, "pg error detail")

        with (
            patches["exp_db_exist"],
            patches["create_empty"],
            patches["drop_database"] as mock_drop,
            patches["subprocess_run"],
        ):
            with pytest.raises(RuntimeError):
                db_mod.restore_db("newdb", zip_dump)

        mock_drop.assert_called_once_with("newdb")

    def test_pg_stderr_not_swallowed_into_generic_message(
        self, db_mod, bypass_db_mgmt, zip_dump
    ):
        pg_msg = 'ERROR: column "foo" of relation "bar" does not exist'
        patches = self._make_patches(db_mod, pg_msg)

        with (
            patches["exp_db_exist"],
            patches["create_empty"],
            patches["drop_database"],
            patches["subprocess_run"],
        ):
            with pytest.raises(RuntimeError) as exc_info:
                db_mod.restore_db("newdb", zip_dump)

        assert pg_msg in str(exc_info.value)

    def test_stderr_captured_not_devnull(self, db_mod, bypass_db_mgmt, zip_dump):
        patches = self._make_patches(db_mod, "any error")

        with (
            patches["exp_db_exist"],
            patches["create_empty"],
            patches["drop_database"],
            patches["subprocess_run"] as mock_run,
        ):
            with pytest.raises(RuntimeError):
                db_mod.restore_db("newdb", zip_dump)

        _args, kwargs = mock_run.call_args
        assert kwargs.get("stderr") == subprocess.PIPE, (
            "subprocess.run must capture stderr=PIPE so pg errors are visible"
        )
        assert kwargs.get("stdout") != subprocess.STDOUT, (
            "stdout=subprocess.STDOUT would redirect stderr to /dev/null"
        )

    def test_restore_creates_target_from_bare_template(
        self, db_mod, bypass_db_mgmt, zip_dump
    ):
        patches = self._make_patches(db_mod, "any error")

        with (
            patches["exp_db_exist"],
            patches["create_empty"] as mock_create,
            patches["drop_database"],
            patches["subprocess_run"],
        ):
            with pytest.raises(RuntimeError):
                db_mod.restore_db("newdb", zip_dump)

        mock_create.assert_called_once_with(
            "newdb", template="template0", force_unaccent=True, setup_if_exists=False
        )


class TestRestoreDbCleanupOnAnyFailure:
    def test_empty_db_dropped_when_zip_is_invalid(self, db_mod, bypass_db_mgmt):
        with tempfile.NamedTemporaryFile(suffix=".zip") as f:
            f.write(b"not a zip file at all")
            f.flush()
            invalid_zip = f.name

            with (
                patch.object(db_mod.restore, "exp_db_exist", return_value=False),
                patch.object(db_mod.restore, "_create_empty_database"),
                patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            ):
                with pytest.raises(RuntimeError, match="Couldn't restore database"):
                    db_mod.restore_db("newdb", invalid_zip)

        mock_drop.assert_called_once_with("newdb")

    def test_empty_db_dropped_when_registry_load_fails(
        self, db_mod, bypass_db_mgmt, zip_dump
    ):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            patch(
                "odoo.service.db.restore.subprocess.run",
                return_value=CompletedProcess(args=[], returncode=0, stderr=""),
            ),
            patch(
                "odoo.modules.registry.Registry.new",
                side_effect=RuntimeError("registry boom"),
            ),
        ):
            with pytest.raises(RuntimeError, match="registry boom"):
                db_mod.restore_db("newdb", zip_dump)

        mock_drop.assert_called_once_with("newdb")


class TestRestoreDbWallClockTimeout:
    def test_timeout_raises_runtimeerror_and_drops_db(
        self, db_mod, bypass_db_mgmt, zip_dump
    ):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            patch(
                "odoo.service.db.restore.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="psql", timeout=1.0),
            ),
        ):
            with pytest.raises(RuntimeError, match="timeout"):
                db_mod.restore_db("newdb", zip_dump)

        mock_drop.assert_called_once_with("newdb")

    def test_timeout_kwarg_passed_to_subprocess(self, db_mod, bypass_db_mgmt, zip_dump):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database"),
            patch(
                "odoo.service.db.restore.subprocess.run",
                return_value=CompletedProcess(args=[], returncode=1, stderr="x"),
            ) as mock_run,
        ):
            with pytest.raises(RuntimeError):
                db_mod.restore_db("newdb", zip_dump)

        _args, kwargs = mock_run.call_args
        assert kwargs.get("timeout", 0) > 0, (
            "restore subprocess must be bounded by a wall-clock timeout"
        )


class TestDumpDbNameValidation:
    @pytest.mark.parametrize("bad_name", ["--version", "-x", "bad name", ".hidden"])
    def test_rejects_flag_shaped_name_before_subprocess(
        self, db_mod, bypass_db_mgmt, bad_name
    ):
        with (
            patch("odoo.service.db.dump.subprocess.Popen") as mock_popen,
            patch.object(db_mod.dump, "get_pg_tool_path") as mock_tool,
        ):
            with pytest.raises(ValueError):
                db_mod.dump_db(bad_name, None, backup_format="dump")
        mock_popen.assert_not_called()
        mock_tool.assert_not_called()

    def test_valid_name_reaches_pg_dump_argv(self, db_mod, bypass_db_mgmt):
        captured = {}

        def fake_popen(cmd, **kw):
            captured["cmd"] = cmd
            return _FakePgDumpPopen(returncode=0)

        with (
            patch("odoo.service.db.dump.subprocess.Popen", side_effect=fake_popen),
            patch.object(db_mod.dump, "get_pg_tool_path", lambda n: f"/usr/bin/{n}"),
            patch.object(db_mod.dump, "exec_pg_environ", dict),
        ):
            result = db_mod.dump_db("gooddb", None, backup_format="dump")
        if result is not None:
            result.close()
        assert "gooddb" in captured["cmd"]


class TestDbNameValidation:
    @pytest.mark.parametrize(
        "bad_name",
        [
            "bad name",
            "-badstart",
            ".badstart",
            "_badstart",
            "",
            "ab!cd",
            "ab/cd",
        ],
    )
    def test_create_rejects_invalid_names(self, db_mod, bypass_db_mgmt, bad_name):
        with patch.object(db_mod.lifecycle, "_create_empty_database") as mock_create:
            with pytest.raises(ValueError, match="Invalid database name"):
                db_mod.exp_create_database(bad_name, False, "en_US")
        mock_create.assert_not_called()

    @pytest.mark.parametrize(
        "good_name",
        [
            "mydb",
            "my-db",
            "my_db",
            "my.db",
            "My_DB-1.0",
            "a1",
        ],
    )
    def test_create_accepts_valid_names(self, db_mod, bypass_db_mgmt, good_name):
        with (
            patch.object(db_mod.lifecycle, "_create_empty_database"),
            patch("odoo.modules.db.initialize_db"),
        ):
            db_mod.exp_create_database(good_name, False, "en_US")

    @pytest.mark.parametrize("bad_name", ["bad name", "-start", "has/slash"])
    def test_duplicate_rejects_invalid_new_name(self, db_mod, bypass_db_mgmt, bad_name):
        with pytest.raises(ValueError, match="Invalid database name"):
            db_mod.duplicate_database("source_db", bad_name)


class TestRestoreDbTypeCheck:
    @pytest.mark.parametrize("bad_arg", [42, None, b"bytes", 2.5, ["list"]])
    def test_raises_type_error(self, db_mod, bypass_db_mgmt, bad_arg):
        with pytest.raises(TypeError, match="db must be a str"):
            db_mod.restore_db(bad_arg, "/dev/null")

    def test_str_passes_type_check(self, db_mod, bypass_db_mgmt):
        with patch.object(db_mod.restore, "exp_db_exist", return_value=True):
            with pytest.raises(RuntimeError, match="already exists"):
                db_mod.restore_db("valid_str", "/dev/null")


class _FakePgDumpPopen:
    def __init__(self, returncode: int = 0, stderr: bytes = b"", stdout: bytes = b""):
        self.returncode = returncode
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.terminated = False
        self.killed = False

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


class TestDumpDbZipStderr:
    def _patches(self, db_mod, returncode: int, stderr: bytes) -> list:
        mock_db, _mock_cr = fake_pg_connection()
        return [
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch("odoo.db.db_connect", return_value=mock_db),
            patch.object(
                db_mod.dump, "dump_db_manifest", return_value={"odoo_dump": "1"}
            ),
            patch(
                "odoo.service.db.dump.subprocess.Popen",
                return_value=_FakePgDumpPopen(returncode=returncode, stderr=stderr),
            ),
        ]

    def test_failure_raises_runtime_error(self, db_mod, bypass_db_mgmt):
        with ExitStack() as stack:
            for p in self._patches(
                db_mod, returncode=1, stderr=b"pg_dump: error: conn failed"
            ):
                stack.enter_context(p)
            with pytest.raises(RuntimeError, match="pg_dump failed"):
                db_mod.dump_db("testdb", None, "zip", with_filestore=False)

    def test_failure_includes_pg_stderr_text(self, db_mod, bypass_db_mgmt):
        pg_err = b'FATAL: role "odoo" does not exist'
        with ExitStack() as stack:
            for p in self._patches(db_mod, returncode=1, stderr=pg_err):
                stack.enter_context(p)
            with pytest.raises(RuntimeError) as exc_info:
                db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        assert 'role "odoo" does not exist' in str(exc_info.value)

    def test_subprocess_called_with_stderr_pipe(self, db_mod, bypass_db_mgmt):
        with ExitStack() as stack:
            for p in self._patches(db_mod, returncode=1, stderr=b"err")[:-1]:
                stack.enter_context(p)
            mock_popen = stack.enter_context(
                patch(
                    "odoo.service.db.dump.subprocess.Popen",
                    return_value=_FakePgDumpPopen(returncode=1, stderr=b"err"),
                )
            )
            with pytest.raises(RuntimeError):
                db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        _args, kwargs = mock_popen.call_args
        assert kwargs.get("stderr") == subprocess.PIPE
        assert kwargs.get("stdout") == subprocess.PIPE
        assert kwargs.get("stdout") != subprocess.STDOUT

    def test_zip_pg_dump_no_longer_writes_an_uncompressed_dump_to_disk(
        self, db_mod, bypass_db_mgmt
    ):
        with ExitStack() as stack:
            for p in self._patches(db_mod, returncode=0, stderr=b"")[:-1]:
                stack.enter_context(p)
            mock_popen = stack.enter_context(
                patch(
                    "odoo.service.db.dump.subprocess.Popen",
                    return_value=_FakePgDumpPopen(returncode=0, stderr=b""),
                )
            )
            db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        cmd = mock_popen.call_args[0][0]
        assert not any(str(a).startswith("--file=") for a in cmd), cmd


class TestDumpDbZipLargeSqlMember:
    def _patches(self, db_mod, stdout: bytes, zip64_limit: int) -> list:
        mock_db, _mock_cr = fake_pg_connection()
        return [
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch("odoo.db.db_connect", return_value=mock_db),
            patch.object(
                db_mod.dump, "dump_db_manifest", return_value={"odoo_dump": "1"}
            ),
            patch(
                "odoo.service.db.dump.subprocess.Popen",
                return_value=_FakePgDumpPopen(stdout=stdout),
            ),
            patch.object(zipfile, "ZIP64_LIMIT", zip64_limit),
        ]

    def test_sql_member_over_the_zip64_limit_round_trips(self, db_mod, bypass_db_mgmt):
        sql = b"-- oversized dump\n" + b"x" * 4096
        with ExitStack() as stack:
            for p in self._patches(db_mod, sql, zip64_limit=64):
                stack.enter_context(p)
            dump = db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        assert dump is not None
        with dump, zipfile.ZipFile(dump) as zf:
            assert zf.testzip() is None
            assert zf.read("dump.sql") == sql

    def test_sql_member_under_the_limit_is_unaffected(self, db_mod, bypass_db_mgmt):
        sql = b"-- small dump\n"
        with ExitStack() as stack:
            for p in self._patches(db_mod, sql, zip64_limit=zipfile.ZIP64_LIMIT):
                stack.enter_context(p)
            dump = db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        assert dump is not None
        with dump, zipfile.ZipFile(dump) as zf:
            assert zf.read("dump.sql") == sql


class TestDumpDbZipManifestBeforeFilestore:
    def test_unreachable_db_fails_before_filestore_copy(self, db_mod, tmp_path):
        import psycopg

        filestore = tmp_path / "filestore"
        filestore.mkdir()
        (filestore / "blob.bin").write_bytes(b"x" * 16)

        class _Cfg(dict):
            def filestore(self, name: str) -> str:
                return str(filestore)

        import odoo.tools

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(odoo.tools, "config", _Cfg({"list_db": True}))
            )
            stack.enter_context(
                patch(
                    "odoo.service.db.dump.get_pg_tool_path",
                    return_value="/usr/bin/pg_dump",
                )
            )
            stack.enter_context(
                patch("odoo.service.db.dump.exec_pg_environ", return_value={})
            )
            stack.enter_context(
                patch(
                    "odoo.db.db_connect", side_effect=psycopg.OperationalError("down")
                )
            )
            copytree = stack.enter_context(
                patch("odoo.service.db.dump.shutil.copytree")
            )
            with pytest.raises(psycopg.OperationalError):
                db_mod.dump_db("testdb", None, "zip", with_filestore=True)
        copytree.assert_not_called()


class TestDumpDbWallClockTimeout:
    def _patches(self, db_mod, run_side_effect) -> list:
        mock_db, _mock_cr = fake_pg_connection()
        return [
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch("odoo.db.db_connect", return_value=mock_db),
            patch.object(
                db_mod.dump, "dump_db_manifest", return_value={"odoo_dump": "1"}
            ),
            patch("odoo.service.db.dump.subprocess.run", side_effect=run_side_effect),
        ]

    def test_zip_path_arms_the_wall_clock_stall_timer(self, db_mod, bypass_db_mgmt):
        armed = []

        class _SpyTimer(threading.Timer):
            def __init__(self, interval, function, *a, **kw):
                armed.append(interval)
                super().__init__(interval, function, *a, **kw)

        with ExitStack() as stack:
            for p in self._patches(db_mod, run_side_effect=None)[:-1]:
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "odoo.service.db.dump.subprocess.Popen",
                    return_value=_FakePgDumpPopen(returncode=0),
                )
            )
            stack.enter_context(patch.object(db_mod.dump.threading, "Timer", _SpyTimer))
            db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        assert armed == [3600.0], (
            "zip-format pg_dump must be bounded by a wall-clock timeout"
        )

    def test_zip_path_timeout_raises_runtime_error(self, db_mod, bypass_db_mgmt):
        proc = _FakePgDumpPopen(returncode=-15, stderr=b"")

        class _FiringTimer(threading.Timer):
            def start(self):
                self.function()

        with ExitStack() as stack:
            for p in self._patches(db_mod, run_side_effect=None)[:-1]:
                stack.enter_context(p)
            stack.enter_context(
                patch("odoo.service.db.dump.subprocess.Popen", return_value=proc)
            )
            stack.enter_context(
                patch.object(db_mod.dump.threading, "Timer", _FiringTimer)
            )
            with pytest.raises(RuntimeError, match="wall-clock timeout"):
                db_mod.dump_db("testdb", None, "zip", with_filestore=False)
        assert proc.terminated, "a stalled pg_dump must be signalled, not just failed"

    def test_custom_nonstream_timeout_raises_runtime_error(
        self, db_mod, bypass_db_mgmt
    ):
        proc = _FakePgDumpPopen(returncode=-15, stderr=b"")

        class _FiringTimer(threading.Timer):
            def start(self):
                self.function()

        with ExitStack() as stack:
            for p in self._patches(db_mod, run_side_effect=None)[:-1]:
                stack.enter_context(p)
            stack.enter_context(
                patch("odoo.service.db.dump.subprocess.Popen", return_value=proc)
            )
            stack.enter_context(
                patch.object(db_mod.dump.threading, "Timer", _FiringTimer)
            )
            with pytest.raises(RuntimeError, match="wall-clock timeout"):
                db_mod.dump_db("testdb", None, "dump", with_filestore=False)
        assert proc.terminated

    def test_malformed_timeout_env_falls_back_to_default(self, db_mod):
        with patch.dict(os.environ, {"ODOO_PG_DUMP_TOTAL_TIMEOUT": "not-a-number"}):
            assert db_mod.dump._get_pg_dump_total_timeout() == 3600.0


class TestDumpWaitTimeoutGuard:
    def test_malformed_wait_timeout_does_not_crash_streaming_dump(self, db_mod):
        cmd = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'dump-bytes')",
        ]
        out = io.BytesIO()
        with patch.dict(os.environ, {"ODOO_PG_DUMP_WAIT_TIMEOUT": "not-a-number"}):
            db_mod.dump._run_pg_dump(cmd, dict(os.environ), out)
        assert out.getvalue() == b"dump-bytes"

    def test_malformed_wait_timeout_does_not_mask_copy_error(self, db_mod):
        class _ExplodingStream:
            def write(self, _data: bytes) -> int:
                raise RuntimeError("disk-full-during-copy")

        cmd = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 1000)"]
        with patch.dict(os.environ, {"ODOO_PG_DUMP_WAIT_TIMEOUT": "garbage"}):
            with pytest.raises(RuntimeError, match="disk-full-during-copy"):
                db_mod.dump._run_pg_dump(cmd, dict(os.environ), _ExplodingStream())


class TestDumpStreamingClosesItsPipes:
    def test_no_resource_warning_and_both_pipes_closed(self, db_mod):
        cmd = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'dump'); sys.stderr.write('warn')",
        ]
        out = io.BytesIO()
        opened: list = []
        real_popen = subprocess.Popen

        def _tracking_popen(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            opened.append(proc)
            return proc

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            with patch.object(db_mod.dump.subprocess, "Popen", _tracking_popen):
                db_mod.dump._run_pg_dump(cmd, dict(os.environ), out)

        assert out.getvalue() == b"dump"
        assert len(opened) == 1
        proc = opened[0]
        assert proc.stdout.closed, "stdout pipe left open"
        assert proc.stderr.closed, "stderr pipe left open"
        leaked = [w for w in caught if issubclass(w.category, ResourceWarning)]
        assert not leaked, f"unclosed file(s): {[str(w.message) for w in leaked]}"

    def test_failed_dump_does_not_retain_fds_while_error_is_held(self, db_mod):
        class _ExplodingStream:
            def write(self, _data: bytes) -> int:
                raise RuntimeError("disk-full-during-copy")

        cmd = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'x' * 100000)",
        ]

        def open_fds():
            return {p.name for p in pathlib.Path(f"/proc/{os.getpid()}/fd").iterdir()}

        held = []
        before = open_fds()
        for _ in range(5):
            try:
                db_mod.dump._run_pg_dump(cmd, dict(os.environ), _ExplodingStream())
            except RuntimeError as exc:
                held.append(exc)
        retained = open_fds() - before
        assert not retained, (
            f"{len(retained)} fd(s) retained by 5 failed dumps whose errors are "
            f"still referenced"
        )
        assert len(held) == 5


class TestDumpStderrDrainIsBounded:
    def test_orphan_holding_stderr_does_not_block_the_dump(
        self, db_mod, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(db_mod.dump, "_STDERR_DRAIN_JOIN_S", 1.0)
        pidfile = tmp_path / "grandchild.pid"
        grandchild = (
            f"import os, time; open({str(pidfile)!r}, 'w').write(str(os.getpid()));"
            " time.sleep(30)"
        )
        child = (
            "import subprocess, sys\n"
            "sys.stdout.buffer.write(b'dump-bytes'); sys.stdout.buffer.flush()\n"
            f"subprocess.Popen([sys.executable, '-c', {grandchild!r}],"
            " stdout=subprocess.DEVNULL, stderr=sys.stderr)\n"
        )
        cmd = [sys.executable, "-c", child]
        out = io.BytesIO()
        result: dict = {}

        def _run():
            try:
                db_mod.dump._run_pg_dump(cmd, dict(os.environ), out)
                result["ok"] = True
            except BaseException as exc:
                result["exc"] = exc

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=30)
        try:
            assert not t.is_alive(), (
                "streaming dump hung: the stderr drain join is still unbounded"
            )
            assert result.get("ok"), f"dump failed unexpectedly: {result.get('exc')!r}"
            assert out.getvalue() == b"dump-bytes"
        finally:
            with contextlib.suppress(OSError, ValueError):
                os.kill(int(pidfile.read_text()), signal.SIGKILL)


class TestDumpStallSigkillEscalation:
    def test_sigterm_ignoring_dump_is_sigkilled_and_does_not_hang(
        self, db_mod, monkeypatch
    ):
        child = (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "sys.stdout.buffer.write(b'partial'); sys.stdout.buffer.flush()\n"
            "time.sleep(3600)\n"
        )
        cmd = [sys.executable, "-c", child]
        monkeypatch.setattr(db_mod.dump, "_get_pg_dump_total_timeout", lambda: 0.5)
        monkeypatch.setattr(db_mod.dump, "_STALL_SIGKILL_GRACE_S", 0.5)
        out = io.BytesIO()

        result: dict = {}

        def _run() -> None:
            try:
                db_mod.dump._run_pg_dump(cmd, dict(os.environ), out)
                result["ok"] = True
            except BaseException as exc:
                result["exc"] = exc

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=30)
        assert not t.is_alive(), (
            "streaming dump hung: a SIGTERM-ignoring pg_dump was never SIGKILLed"
        )
        assert isinstance(result.get("exc"), RuntimeError)
        assert "wall-clock timeout" in str(result["exc"])


class TestDumpDbDumpFormat:
    def _make_mock_proc(self, stderr: bytes, returncode: int) -> MagicMock:
        proc = MagicMock()
        proc.stdout = io.BytesIO(b"partial output")
        proc.stderr = io.BytesIO(stderr)
        proc.returncode = returncode
        proc.wait.return_value = None
        return proc

    def test_stream_path_raises_on_nonzero_returncode(self, db_mod, bypass_db_mgmt):
        proc = self._make_mock_proc(b"pg_dump: error: boom", returncode=1)
        with (
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch("odoo.service.db.dump.subprocess.Popen", return_value=proc),
        ):
            with pytest.raises(RuntimeError, match="pg_dump failed"):
                db_mod.dump_db("testdb", io.BytesIO(), "dump")

    def test_stream_path_stderr_in_error_message(self, db_mod, bypass_db_mgmt):
        pg_err = b"FATAL: authentication failed for user"
        proc = self._make_mock_proc(pg_err, returncode=1)
        with (
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch("odoo.service.db.dump.subprocess.Popen", return_value=proc),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                db_mod.dump_db("testdb", io.BytesIO(), "dump")
        assert "FATAL: authentication failed" in str(exc_info.value)

    def test_stream_path_success_returns_none(self, db_mod, bypass_db_mgmt):
        proc = self._make_mock_proc(b"", returncode=0)
        with (
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch("odoo.service.db.dump.subprocess.Popen", return_value=proc),
        ):
            result = db_mod.dump_db("testdb", io.BytesIO(), "dump")
        assert result is None

    def test_no_stream_path_raises_on_nonzero_returncode(self, db_mod, bypass_db_mgmt):
        with (
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch(
                "odoo.service.db.dump.subprocess.Popen",
                return_value=_FakePgDumpPopen(returncode=1, stderr=b"pg error"),
            ),
        ):
            with pytest.raises(RuntimeError, match="pg_dump failed"):
                db_mod.dump_db("testdb", None, "dump")

    def test_no_stream_path_returns_seekable_tempfile(self, db_mod, bypass_db_mgmt):
        with (
            patch(
                "odoo.service.db.dump.get_pg_tool_path", return_value="/usr/bin/pg_dump"
            ),
            patch("odoo.service.db.dump.exec_pg_environ", return_value={}),
            patch(
                "odoo.service.db.dump.subprocess.Popen",
                return_value=_FakePgDumpPopen(returncode=0, stdout=b"PGDMP"),
            ),
        ):
            result = db_mod.dump_db("testdb", None, "dump")
        assert result is not None, "Must return a file object, not None or proc.stdout"
        assert hasattr(result, "seek"), (
            "Returned object must be seekable (TemporaryFile)"
        )
        result.close()


class TestCheckFaketimeMode:
    def test_noop_when_env_var_absent(self, db_mod):
        import os

        import odoo.tools

        os.environ.pop("ODOO_FAKETIME_TEST_MODE", None)
        with (
            patch.object(odoo.tools, "config", {"test_enable": True, "db_name": ["x"]}),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect") as mock_connect,
        ):
            db_mod.lifecycle._create_faketime_now_function("x")

        mock_connect.assert_not_called()

    def test_noop_when_test_enable_off_with_env_var(self, db_mod, caplog):
        import odoo.tools

        with (
            patch.dict("os.environ", {"ODOO_FAKETIME_TEST_MODE": "1"}),
            patch.object(
                odoo.tools, "config", {"test_enable": False, "db_name": ["x"]}
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect") as mock_connect,
            caplog.at_level("WARNING", logger="odoo.service.db"),
        ):
            db_mod.lifecycle._create_faketime_now_function("x")

        mock_connect.assert_not_called()
        assert any("Refusing to install faketime" in m for m in caplog.messages)

    def test_noop_when_db_not_in_config(self, db_mod):
        import odoo.tools

        with (
            patch.dict("os.environ", {"ODOO_FAKETIME_TEST_MODE": "1"}),
            patch.object(
                odoo.tools, "config", {"test_enable": True, "db_name": ["other"]}
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect") as mock_connect,
        ):
            db_mod.lifecycle._create_faketime_now_function("unlisted_db")

        mock_connect.assert_not_called()

    def test_active_when_all_gates_pass(self, db_mod):
        import datetime

        import odoo.tools

        fake_now = datetime.datetime(2026, 1, 1)
        fake_db, fake_cursor = fake_pg_connection(
            fetchone_sequence=[(fake_now,), (fake_now,)]
        )

        with (
            patch.dict("os.environ", {"ODOO_FAKETIME_TEST_MODE": "1"}),
            patch.object(odoo.tools, "config", {"test_enable": True, "db_name": ["x"]}),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db),
        ):
            db_mod.lifecycle._create_faketime_now_function("x")

        assert any(
            "CREATE OR REPLACE FUNCTION" in str(call_args)
            for call_args in fake_cursor.execute.call_args_list
        )


class TestCreateEmptyDatabaseTOCTOU:
    def test_duplicate_database_translates_to_databaseexists(self, db_mod):
        import psycopg

        import odoo.tools

        fake_db, _fake_cr = fake_pg_connection(
            execute=psycopg.errors.DuplicateDatabase('database "x" already exists')
        )

        with (
            patch.object(
                odoo.tools, "config", {"db_template": "template0", "unaccent": False}
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db),
            patch("odoo.service.db.lifecycle.get_database_identifier", return_value=""),
            patch("odoo.service.db.lifecycle._create_faketime_now_function"),
        ):
            with pytest.raises(db_mod.DatabaseExists, match="already exists"):
                db_mod._create_empty_database("x")

    def test_creation_is_the_first_statement_issued(self, db_mod):
        import odoo.tools

        executed = []
        fake_db, _fake_cr = fake_pg_connection(
            execute=lambda sql, *a, **kw: executed.append(str(sql))
        )

        with (
            patch.object(
                odoo.tools,
                "config",
                {"db_template": "template0", "unaccent": False},
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db),
            patch(
                "odoo.service.db.lifecycle.get_database_identifier", return_value="x"
            ),
            patch("odoo.service.db.lifecycle._create_faketime_now_function"),
        ):
            db_mod._create_empty_database("x")

        assert executed, "no SQL was issued at all"
        assert "CREATE DATABASE" in executed[0].upper(), (
            f"a statement ran before CREATE DATABASE, reopening the TOCTOU "
            f"window: {executed[0]!r}"
        )


class TestRestoreDbZipSlip:
    @pytest.fixture
    def malicious_zip(self):
        made = []

        def _make(escaping_name: str) -> str:
            fd = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)  # noqa: SIM115
            with zipfile.ZipFile(fd, "w") as zf:
                zf.writestr("dump.sql", "SELECT 1;")
                zf.writestr(escaping_name, b"payload")
            fd.close()
            made.append(fd.name)
            return fd.name

        yield _make
        for path in made:
            pathlib.Path(path).unlink()

    @pytest.mark.parametrize(
        "escaping_name",
        [
            "../evil.sql",
            "../../etc/cron.d/pwn",
            "filestore/../../../tmp/escape",
            "/abs/evil",
        ],
    )
    def test_escaping_member_is_refused_behaviorally(
        self, db_mod, bypass_db_mgmt, malicious_zip, escaping_name
    ):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            patch("odoo.service.db.restore.subprocess.run") as mock_run,
        ):
            with pytest.raises(RuntimeError, match="escapes the extraction directory"):
                db_mod.restore_db("newdb", malicious_zip(escaping_name))
            mock_run.assert_not_called()
        mock_drop.assert_called_once_with("newdb")


class TestExpRestoreBase64Decoder:
    @staticmethod
    def _decode_via_exp_restore(db_mod, b64_text: str) -> bytes:
        captured = {}

        def _capture(db, dump_file, copy=False, neutralize_database=False):
            captured["bytes"] = pathlib.Path(dump_file).read_bytes()

        with patch.object(db_mod.restore, "restore_db", side_effect=_capture):
            db_mod.exp_restore("dummy", b64_text)
        return captured["bytes"]

    @pytest.mark.parametrize("size", [0, 1, 2, 3, 4, 5, 100, 8192, 8193, 12000])
    def test_clean_base64_round_trips(self, db_mod, bypass_db_mgmt, size):
        import base64

        payload = bytes((i * 7 + 3) % 256 for i in range(size))
        b64 = base64.b64encode(payload).decode("ascii")
        assert self._decode_via_exp_restore(db_mod, b64) == payload

    def test_wrapped_and_padded_whitespace_round_trips(self, db_mod, bypass_db_mgmt):
        import base64

        payload = bytes((i * 13) % 256 for i in range(10000))
        b64 = base64.b64encode(payload).decode("ascii")
        wrapped = "\n".join(b64[i : i + 76] for i in range(0, len(b64), 76))
        wrapped = "  \r\n" + wrapped.replace("A", "A\t", 1) + "\n\n  "
        assert self._decode_via_exp_restore(db_mod, wrapped) == payload


class TestExpDumpMemory:
    def test_dump_is_streamed_in_bounded_reads(self, db_mod, bypass_db_mgmt):
        def read_sizes_for(dump_bytes):
            sizes = []
            real_tempfile = tempfile.TemporaryFile

            def instrumented(*args, **kwargs):
                handle = real_tempfile(*args, **kwargs)
                real_read = handle.read

                def read(size=-1, /):
                    sizes.append(size)
                    return real_read(size)

                handle.read = read
                return handle

            def fake_dump_db(db_name, stream, backup_format):
                stream.write(b"x" * dump_bytes)

            with (
                patch("odoo.service.db.dump.tempfile.TemporaryFile", instrumented),
                patch.object(db_mod.dump, "dump_db", fake_dump_db),
                patch.object(db_mod.dump, "check_db_exposed"),
            ):
                db_mod.exp_dump("mydb", "zip")
            return sizes

        small = read_sizes_for(4 * 1024 * 1024)
        large = read_sizes_for(16 * 1024 * 1024)

        assert small and large, "exp_dump issued no read at all"
        assert all(size > 0 for size in small + large), (
            f"exp_dump asked for an unbounded read: {small + large!r}. "
            f"``read(-1)`` materialises the whole dump exactly like ``read()``"
        )
        assert max(small) == max(large), (
            f"read size scales with dump size ({max(small)} -> {max(large)}); it "
            f"must be a fixed chunk, or peak memory grows with the database"
        )
        assert len(large) > len(small), (
            "a four-times-larger dump must take more reads, not bigger ones"
        )

    def test_dump_output_matches_b64encode_of_raw(self, db_mod, bypass_db_mgmt):
        import base64

        payload = b"hello world " * 1000

        def fake_dump_db(db_name, stream, backup_format):
            stream.write(payload)

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["testdb"]),
            patch.object(db_mod.dump, "dump_db", side_effect=fake_dump_db),
        ):
            encoded = db_mod.exp_dump("testdb", "zip")

        assert encoded == base64.b64encode(payload).decode("ascii")

    def test_dump_accepts_backup_format_kwarg(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["testdb"]),
            patch.object(db_mod.dump, "dump_db"),
        ):
            db_mod.exp_dump("testdb", backup_format="zip")


class TestCheckDbExposed:
    def test_raises_access_denied_for_unlisted_db(self, db_mod):
        import odoo.exceptions

        with patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]):
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.check_db_exposed("other")

    def test_passes_silently_for_listed_db(self, db_mod):
        with patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]):
            assert db_mod.check_db_exposed("exposed") is None

    def test_logs_warning_with_db_name_before_raising(self, db_mod, caplog):
        import odoo.exceptions

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            caplog.at_level("WARNING", logger="odoo.service.db"),
        ):
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.check_db_exposed("secret_db")
        assert any("secret_db" in m for m in caplog.messages)

    def test_consults_list_dbs_with_force(self, db_mod):
        with patch.object(
            db_mod.listing, "list_dbs", return_value=["exposed"]
        ) as mock_list:
            db_mod.check_db_exposed("exposed")
        mock_list.assert_called_once_with(True)


class TestListDbsConfiguredNamesAreAnAssertion:
    def test_configured_names_are_returned_without_consulting_the_catalogue(
        self, db_mod
    ):
        import odoo.db

        with (
            patch.object(
                odoo.tools,
                "config",
                {
                    "list_db": True,
                    "dbfilter": "",
                    "db_name": ["definitely_not_a_db_xyz"],
                },
            ),
            patch.object(odoo.db, "db_connect") as connect,
        ):
            assert db_mod.list_dbs(True) == ["definitely_not_a_db_xyz"]
        connect.assert_not_called()

    def test_check_db_exposed_admits_a_configured_name_that_no_longer_exists(
        self, db_mod
    ):
        import odoo.db

        with (
            patch.object(
                odoo.tools,
                "config",
                {
                    "list_db": True,
                    "dbfilter": "",
                    "db_name": ["definitely_not_a_db_xyz"],
                },
            ),
            patch.object(odoo.db, "db_connect") as connect,
        ):
            assert db_mod.check_db_exposed("definitely_not_a_db_xyz") is None
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.check_db_exposed("some_other_real_db")
        connect.assert_not_called()

    def test_rpc_db_exist_does_not_inherit_that_looseness(self, db_mod):
        import odoo.tools

        with (
            patch.object(
                odoo.tools,
                "config",
                {
                    "list_db": True,
                    "dbfilter": "",
                    "db_name": ["definitely_not_a_db_xyz"],
                    "db_template": "template0",
                },
            ),
            patch.object(db_mod.listing, "exp_db_exist", return_value=False) as exists,
        ):
            assert db_mod.listing._rpc_db_exist("definitely_not_a_db_xyz") is False
        exists.assert_called_once_with("definitely_not_a_db_xyz")


class TestExpDumpAllowlistGate:
    def test_rejects_db_outside_allowlist(self, db_mod, bypass_db_mgmt):
        import odoo.exceptions

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(db_mod.dump, "dump_db") as mock_dump,
        ):
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.exp_dump("other", "zip")
        mock_dump.assert_not_called()

    def test_allows_db_inside_allowlist(self, db_mod, bypass_db_mgmt):
        import base64

        payload = b"content" * 500

        def fake_dump_db(db_name, stream, backup_format):
            stream.write(payload)

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(db_mod.dump, "dump_db", side_effect=fake_dump_db),
        ):
            encoded = db_mod.exp_dump("exposed", "zip")

        assert encoded == base64.b64encode(payload).decode("ascii")


class TestExpMigrateDatabasesAllowlistGate:
    def test_rejects_when_any_db_outside_allowlist(self, db_mod, bypass_db_mgmt):
        import odoo.exceptions

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["a", "b"]),
            patch("odoo.modules.registry.Registry.new") as mock_new,
        ):
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.exp_migrate_databases(["a", "c"])
        mock_new.assert_not_called()

    def test_accepts_when_all_in_allowlist(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["a", "b"]),
            patch("odoo.modules.registry.Registry.new") as mock_new,
        ):
            result = db_mod.exp_migrate_databases(["a", "b"])
        assert result is True
        assert mock_new.call_count == 2

    def test_empty_list_is_noop_success(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["a"]),
            patch("odoo.modules.registry.Registry.new") as mock_new,
        ):
            result = db_mod.exp_migrate_databases([])
        assert result is True
        mock_new.assert_not_called()


class TestExpRenameAllowlistGate:
    def test_rejects_old_name_outside_allowlist(self, db_mod, bypass_db_mgmt):
        import odoo.exceptions

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(db_mod.lifecycle, "rename_database") as mock_inner,
        ):
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.exp_rename("other", "newname")
        mock_inner.assert_not_called()

    def test_passes_through_to_inner_when_exposed(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(
                db_mod.lifecycle, "rename_database", return_value=True
            ) as mock_inner,
        ):
            result = db_mod.exp_rename("exposed", "newname")
        assert result is True
        mock_inner.assert_called_once_with("exposed", "newname")

    def test_new_name_not_checked_against_allowlist(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(
                db_mod.lifecycle, "rename_database", return_value=True
            ) as mock_inner,
        ):
            db_mod.exp_rename("exposed", "brand_new_target")
        mock_inner.assert_called_once_with("exposed", "brand_new_target")

    def test_internal_helper_does_not_consult_allowlist(self, db_mod):
        with patch.object(db_mod.listing, "list_dbs") as mock_list:
            with pytest.raises(ValueError):
                db_mod.rename_database("any_unexposed", "bad name")
        mock_list.assert_not_called()


class TestExpDuplicateAllowlistGate:
    def test_rejects_source_outside_allowlist(self, db_mod, bypass_db_mgmt):
        import odoo.exceptions

        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(db_mod.lifecycle, "duplicate_database") as mock_inner,
        ):
            with pytest.raises(odoo.exceptions.AccessDenied):
                db_mod.exp_duplicate_database("other", "newdb")
        mock_inner.assert_not_called()

    def test_passes_through_to_inner_when_exposed(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(
                db_mod.lifecycle, "duplicate_database", return_value=True
            ) as mock_inner,
        ):
            result = db_mod.exp_duplicate_database(
                "exposed", "newdb", neutralize_database=True
            )
        assert result is True
        mock_inner.assert_called_once_with("exposed", "newdb", True)

    def test_target_name_not_checked_against_allowlist(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.listing, "list_dbs", return_value=["exposed"]),
            patch.object(
                db_mod.lifecycle, "duplicate_database", return_value=True
            ) as mock_inner,
        ):
            db_mod.exp_duplicate_database("exposed", "brand_new_target")
        mock_inner.assert_called_once()

    def test_internal_helper_does_not_consult_allowlist(self, db_mod):
        with patch.object(db_mod.listing, "list_dbs") as mock_list:
            with pytest.raises(ValueError):
                db_mod.duplicate_database("any_unexposed", "bad name")
        mock_list.assert_not_called()


class TestRestoreDbCleanupHelper:
    def test_rollback_survives_list_db_being_turned_off_mid_restore(
        self, db_mod, zip_dump
    ):
        config = _FlippingListDb({"list_db": True})
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", config),
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            patch(
                "odoo.service.db.restore.subprocess.run",
                side_effect=OSError("psql gone"),
            ),
        ):
            with pytest.raises(OSError, match="psql gone"):
                db_mod.restore_db("halfbuilt", zip_dump)

        mock_drop.assert_called_once_with("halfbuilt")
        assert config.reads == 1, (
            f"list_db was consulted {config.reads} times; the rollback re-entered "
            f"a gated verb instead of calling drop_database directly"
        )

    def test_rollback_does_not_re_enter_the_rpc_verb(self, db_mod, zip_dump):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            patch.object(db_mod.lifecycle, "exp_drop") as mock_exp_drop,
            patch(
                "odoo.service.db.restore.subprocess.run",
                side_effect=OSError("psql gone"),
            ),
            patch.object(
                __import__("odoo.tools", fromlist=["config"]),
                "config",
                _MockConfig({"list_db": True}),
            ),
        ):
            with pytest.raises(OSError, match="psql gone"):
                db_mod.restore_db("halfbuilt", zip_dump)

        mock_drop.assert_called_once_with("halfbuilt")
        mock_exp_drop.assert_not_called()


class TestDropDatabaseRetry:
    @pytest.fixture
    def drop_env(self, db_mod, tmp_path):
        fake_db, fake_cr = fake_pg_connection(fetchone=(1,))

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(db_mod.listing, "list_dbs", return_value=["x"])
            )
            stack.enter_context(
                patch.object(db_mod.lifecycle.odoo.modules.registry.Registry, "remove")
            )
            stack.enter_context(patch.object(db_mod.lifecycle.odoo.db, "close_db"))
            stack.enter_context(
                patch(
                    "odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db
                )
            )
            stack.enter_context(
                patch(
                    "odoo.service.db.lifecycle.get_database_identifier", return_value=""
                )
            )
            stack.enter_context(patch("odoo.service.db.lifecycle.time.sleep"))
            stack.enter_context(
                patch(
                    "odoo.service.db.lifecycle.odoo.tools.config.filestore",
                    return_value=str(tmp_path / "nonexistent"),
                    create=True,
                )
            )
            yield fake_cr

    def test_successful_drop_on_first_try(self, db_mod, drop_env):
        result = db_mod.drop_database("x")

        assert result is True
        drop_calls = [
            c for c in drop_env.execute.call_args_list if "DROP DATABASE" in str(c)
        ]
        assert len(drop_calls) == 1

    def test_absent_database_returns_false_without_dropping(self, db_mod, drop_env):
        drop_env.fetchone.return_value = None

        result = db_mod.drop_database("gone")

        assert result is False
        assert not [
            c for c in drop_env.execute.call_args_list if "DROP DATABASE" in str(c)
        ], "issued DROP DATABASE against a database the probe said was absent"

    def test_retries_on_object_in_use_then_succeeds(self, db_mod, drop_env):
        import psycopg

        call_log: list[str] = []

        def execute_side_effect(sql, *args, **kwargs):
            call_log.append(str(sql))
            if "DROP DATABASE" in str(sql):
                if sum("DROP DATABASE" in c for c in call_log) == 1:
                    raise psycopg.errors.ObjectInUse("still connected")

        drop_env.execute.side_effect = execute_side_effect

        result = db_mod.drop_database("x")

        assert result is True
        drops = [c for c in call_log if "DROP DATABASE" in c]
        terminates = [c for c in call_log if "pg_terminate_backend" in c]
        assert len(drops) == 2
        assert len(terminates) == 2

    def test_raises_after_max_retries(self, db_mod, drop_env):
        import psycopg

        def execute_side_effect(sql, *args, **kwargs):
            if "DROP DATABASE" in str(sql):
                raise psycopg.errors.ObjectInUse("forever in use")

        drop_env.execute.side_effect = execute_side_effect

        with pytest.raises(RuntimeError, match="forever in use"):
            db_mod.drop_database("x")


class TestDbnamePattern:
    @pytest.mark.parametrize(
        "name",
        [
            "a",
            "A",
            "0",
            "a1",
            "agromarin",
            "mydb",
            "my-db",
            "my_db",
            "my.db",
            "My_DB-1.0",
            "mdb_1.test-2",
        ],
    )
    def test_accepts_valid_names(self, db_mod, name):
        import re

        assert re.match(db_mod.DBNAME_PATTERN, name), name

    @pytest.mark.parametrize(
        "name", ["", "_leading_underscore", ".dotfirst", "-dashfirst"]
    )
    def test_rejects_invalid_names(self, db_mod, name):
        import re

        assert not re.match(db_mod.DBNAME_PATTERN, name), name


class TestValidateDbNameLengthBoundary:
    def test_exactly_the_maximum_is_accepted(self, db_mod):
        name = "a" * db_mod.DBNAME_MAX_LENGTH
        db_mod.check_db_name(name)

    def test_one_over_the_maximum_is_refused(self, db_mod):
        name = "a" * (db_mod.DBNAME_MAX_LENGTH + 1)
        with pytest.raises(ValueError, match="63 characters"):
            db_mod.check_db_name(name)

    def test_the_length_check_runs_before_the_regex(self, db_mod):
        with pytest.raises(ValueError, match="63 characters"):
            db_mod.check_db_name("-" * 5000)


class TestRpcDbExposedGate:
    @pytest.fixture
    def gate(self):
        from odoo.service._dispatch import is_db_rpc_exposed

        return is_db_rpc_exposed

    @pytest.mark.parametrize(
        "db_name", [None, 42, 4.0, True, b"bytes", ["db"], {"db": 1}, object()]
    )
    def test_a_non_string_is_never_exposed(self, gate, db_name):
        assert gate(db_name) is False

    def test_the_empty_string_is_never_exposed(self, gate):
        assert gate("") is False

    @pytest.mark.parametrize("db_name", ["postgres", "template0", "template1"])
    def test_system_databases_are_never_exposed(self, gate, db_name):
        assert gate(db_name) is False

    def test_the_configured_template_is_never_exposed(self, db_mod, gate):
        from odoo.tools import config

        with config.patch(db_template="tpl_custom", db_name=[]):
            assert gate("tpl_custom") is False

    def test_database_option_acts_as_the_allowlist(self, gate):
        from odoo.tools import config

        with config.patch(db_name=["served"]):
            assert gate("served") is True
            assert gate("other") is False

    def test_every_ordinary_name_is_exposed_when_no_allowlist_is_set(self, gate):
        from odoo.tools import config

        with config.patch(db_name=[], dbfilter=""):
            assert gate("anything") is True

    def test_a_static_dbfilter_is_the_allowlist_when_db_name_is_unset(self, gate):
        from odoo.service import _dispatch
        from odoo.tools import config

        _dispatch._compile_static_dbfilter.cache_clear()
        with config.patch(db_name=[], dbfilter="^tenant_a"):
            assert gate("tenant_a_prod") is True
            assert gate("tenant_b_prod") is False

    def test_db_name_wins_over_the_dbfilter(self, gate):
        from odoo.service import _dispatch
        from odoo.tools import config

        _dispatch._compile_static_dbfilter.cache_clear()
        with config.patch(db_name=["served"], dbfilter="^nomatch$"):
            assert gate("served") is True

    @pytest.mark.parametrize("pattern", ["^%h$", "^%d_", "(unclosed"])
    def test_an_unusable_dbfilter_exposes_everything_and_warns_once(
        self, gate, pattern, caplog
    ):
        from odoo.service import _dispatch
        from odoo.tools import config

        _dispatch._compile_static_dbfilter.cache_clear()
        with (
            config.patch(db_name=[], dbfilter=pattern),
            caplog.at_level(logging.WARNING, logger="odoo.service.server"),
        ):
            assert gate("anything") is True
            assert gate("anything_else") is True
        warnings = [
            r
            for r in caplog.records
            if r.name == "odoo.service.server"
            and r.levelno >= logging.WARNING
            and "dbfilter" in r.getMessage()
        ]
        assert len(warnings) == 1


class TestAdminGates:
    def test_correct_master_password_passes(self, db_mod):
        import odoo.tools

        with patch.object(
            odoo.tools.config, "is_valid_admin_password", return_value=True
        ) as verify:
            assert db_mod.check_super("correct") is True
        verify.assert_called_once_with("correct")

    def test_wrong_master_password_is_refused(self, db_mod):
        import odoo.tools
        from odoo.exceptions import AccessDenied

        with patch.object(
            odoo.tools.config, "is_valid_admin_password", return_value=False
        ) as verify:
            with pytest.raises(AccessDenied):
                db_mod.check_super("wrong")
        verify.assert_called_once_with("wrong")

    def test_empty_master_password_is_refused(self, db_mod):
        from odoo.exceptions import AccessDenied

        with pytest.raises(AccessDenied):
            db_mod.check_super("")

    def test_management_gate_blocks_when_list_db_is_false(self, db_mod):
        import odoo.tools
        from odoo.exceptions import AccessDenied

        @db_mod.check_db_management_enabled
        def _op():
            return "ok"

        with patch.object(odoo.tools, "config", {"list_db": False}):
            with pytest.raises(AccessDenied):
                _op()

    def test_management_gate_passes_when_list_db_is_true(self, db_mod):
        import odoo.tools

        @db_mod.check_db_management_enabled
        def _op():
            return "ok"

        with patch.object(odoo.tools, "config", {"list_db": True}):
            assert _op() == "ok"

    def test_the_gate_sits_on_the_rpc_verbs_not_on_the_manifest_reader(self, db_mod):
        import odoo.tools

        cr = MagicMock()
        cr.connection.info.server_version = 180000
        cr.fetchall.return_value = [("base", "19.0.1.3")]
        cr.dbname = "somedb"

        with patch.object(odoo.tools, "config", {"list_db": False}):
            manifest = db_mod.dump_db_manifest(cr)
        assert manifest["db_name"] == "somedb"
        assert manifest["pg_version"] == "18.0"

        from odoo.exceptions import AccessDenied

        for gated in (db_mod.dump_db, db_mod.exp_dump):
            with patch.object(odoo.tools, "config", {"list_db": False}):
                with pytest.raises(AccessDenied):
                    gated("somedb", None)


class TestAdminPasswordComplexity:
    def test_rejects_short_password(self, db_mod):
        with pytest.raises(ValueError, match="at least 8 characters"):
            db_mod.exp_change_admin_password("short")

    def test_rejects_empty_password(self, db_mod):
        with pytest.raises(ValueError, match="at least 8 characters"):
            db_mod.exp_change_admin_password("")

    def test_rejects_non_string(self, db_mod):
        with pytest.raises(TypeError, match="must be a str"):
            db_mod.exp_change_admin_password(12345678)

    def test_accepts_8_char_password(self, db_mod):
        with (
            patch(
                "odoo.service.db.rpc.odoo.tools.config.set_admin_password"
            ) as mock_set,
            patch("odoo.service.db.rpc.odoo.tools.config.save") as mock_save,
        ):
            result = db_mod.exp_change_admin_password("abcdefgh")
        assert result is True
        mock_set.assert_called_once_with("abcdefgh")
        mock_save.assert_called_once_with(["admin_passwd"])


class TestAdminPasswordPersistFailureRollsBack:
    @staticmethod
    def _config(existing_hash):
        cfg = _MockConfig({"list_db": True})
        cfg.options = {} if existing_hash is None else {"admin_passwd": existing_hash}

        def set_admin_password(value):
            cfg.options["admin_passwd"] = f"hashed:{value}"

        cfg.set_admin_password = set_admin_password
        cfg.save = MagicMock(side_effect=OSError("read-only file system"))
        return cfg

    def test_an_existing_password_is_restored(self, db_mod):
        import odoo.tools

        cfg = self._config("hashed:old-password")
        with patch.object(odoo.tools, "config", cfg):
            with pytest.raises(OSError, match="read-only"):
                db_mod.exp_change_admin_password("a-new-password")
        assert cfg.options["admin_passwd"] == "hashed:old-password", (
            "the in-memory hash still holds the new password after the write "
            "failed; the running server and the config file now disagree about "
            "the master credential"
        )

    def test_an_absent_password_is_removed_again(self, db_mod):
        import odoo.tools

        cfg = self._config(None)
        with patch.object(odoo.tools, "config", cfg):
            with pytest.raises(OSError):
                db_mod.exp_change_admin_password("a-new-password")
        assert "admin_passwd" not in cfg.options, f"key left behind: {cfg.options!r}"

    def test_the_failure_is_logged_not_swallowed(self, db_mod, caplog):
        import logging

        import odoo.tools

        cfg = self._config("hashed:old-password")
        with (
            patch.object(odoo.tools, "config", cfg),
            caplog.at_level(logging.ERROR, logger="odoo.service.db.rpc"),
        ):
            with pytest.raises(OSError):
                db_mod.exp_change_admin_password("a-new-password")
        assert any(r.levelno >= logging.ERROR for r in caplog.records), (
            "the reverted password change produced no operator-visible record"
        )

    def test_a_successful_save_keeps_the_new_password(self, db_mod):
        import odoo.tools

        cfg = self._config("hashed:old-password")
        cfg.save = MagicMock()
        with patch.object(odoo.tools, "config", cfg):
            assert db_mod.exp_change_admin_password("a-new-password") is True
        assert cfg.options["admin_passwd"] == "hashed:a-new-password"
        cfg.save.assert_called_once_with(["admin_passwd"])


class TestExpRenameValidation:
    def test_rejects_invalid_new_name(self, db_mod):
        with pytest.raises(ValueError, match="Invalid database name"):
            db_mod.rename_database("old_name", "has spaces")

    def test_rejects_empty_new_name(self, db_mod):
        with pytest.raises(ValueError, match="Invalid database name"):
            db_mod.rename_database("old_name", "")

    def test_rejects_leading_underscore(self, db_mod):
        with pytest.raises(ValueError, match="Invalid database name"):
            db_mod.rename_database("old_name", "_starts_with_underscore")


class TestPublicApiSurface:
    def test_every_exp_function_is_exported(self, db_mod):
        """What the docstring gate was really guarding: the RPC surface.

        It asserted that every `exp_*` carried prose, which the strip pass
        removes on purpose.  The property worth keeping is that the callable
        surface and `__all__` agree -- an `exp_*` absent from `__all__` is
        reachable by RPC and invisible to anything reading the package.
        """
        exposed = {
            name
            for name in dir(db_mod)
            if name.startswith("exp_") and callable(getattr(db_mod, name))
        }
        assert exposed, "no exp_* functions found; is this the right module?"
        assert exposed <= set(db_mod.__all__), (
            f"reachable by RPC but not in __all__: "
            f"{sorted(exposed - set(db_mod.__all__))}"
        )


class TestDispatchInvariants:
    def test_master_password_set_is_subset_of_dispatch(self, db_mod):
        missing = db_mod.rpc._REQUIRES_MASTER_PASSWORD - set(db_mod.rpc._DISPATCH)
        assert not missing, (
            f"_REQUIRES_MASTER_PASSWORD references non-existent dispatch keys: "
            f"{missing}. Either add the handler to _DISPATCH or remove from the "
            f"auth set."
        )

    def test_known_admin_methods_require_master_password(self, db_mod):
        must_require_auth = {
            "create_database",
            "duplicate_database",
            "drop",
            "dump",
            "restore",
            "rename",
            "change_admin_password",
            "migrate_databases",
        }
        missing_auth = must_require_auth - db_mod.rpc._REQUIRES_MASTER_PASSWORD
        assert not missing_auth, (
            f"Methods that must require master password but don't: {missing_auth}"
        )

    def test_public_methods_not_password_gated(self, db_mod):
        public_methods = frozenset(
            {
                "db_exist",
                "list",
                "list_lang",
                "server_version",
                "list_countries",
            }
        )
        gated = public_methods & db_mod.rpc._REQUIRES_MASTER_PASSWORD
        assert not gated, (
            f"Public dispatch endpoints incorrectly listed in "
            f"_REQUIRES_MASTER_PASSWORD: {sorted(gated)}. These read "
            f"non-sensitive data and are invoked by unauthenticated UI "
            f"and wizard callers."
        )

    def test_dispatch_list_countries_no_password(self, db_mod):
        mock_handler = MagicMock(return_value=[["MX", "Mexico"]])
        with (
            patch.object(db_mod.rpc, "check_super") as mock_check,
            patch.dict(db_mod.rpc._DISPATCH, {"list_countries": mock_handler}),
        ):
            result = db_mod.dispatch("list_countries", [])
        mock_check.assert_not_called()
        mock_handler.assert_called_once_with()
        assert result == [["MX", "Mexico"]]

    def test_no_legacy_dual_dict_remains(self, db_mod):
        assert not hasattr(db_mod, "_DISPATCH_PUBLIC"), (
            "_DISPATCH_PUBLIC has been replaced by single _DISPATCH + _REQUIRES_MASTER_PASSWORD"
        )
        assert not hasattr(db_mod, "_DISPATCH_ADMIN"), (
            "_DISPATCH_ADMIN has been replaced by single _DISPATCH + _REQUIRES_MASTER_PASSWORD"
        )

    def test_dispatch_calls_check_super_for_admin_method(self, db_mod):
        with (
            patch.object(db_mod.rpc, "check_super") as mock_check,
            patch.object(db_mod.rpc, "exp_drop") as mock_drop,
        ):
            with patch.dict(db_mod.rpc._DISPATCH, {"drop": mock_drop}):
                db_mod.dispatch("drop", ["secret_password", "mydb"])
        mock_check.assert_called_once_with("secret_password")
        mock_drop.assert_called_once_with("mydb")

    def test_dispatch_skips_check_super_for_public_method(self, db_mod):
        mock_handler = MagicMock(return_value=True)
        with (
            patch.object(db_mod.rpc, "check_super") as mock_check,
            patch.dict(db_mod.rpc._DISPATCH, {"db_exist": mock_handler}),
        ):
            result = db_mod.dispatch("db_exist", ["mydb"])
        mock_check.assert_not_called()
        mock_handler.assert_called_once_with("mydb")
        assert result is True

    _ALLOWLIST_EXEMPT = frozenset(
        {
            "create_database",
            "restore",
            "change_admin_password",
        }
    )

    _UNEXPOSED_CALL = {
        "drop": ("hidden_db",),
        "dump": ("hidden_db", "zip"),
        "duplicate_database": ("hidden_db", "copy_db"),
        "migrate_databases": (["hidden_db"],),
        "rename": ("hidden_db", "new_db"),
    }

    def test_db_name_handlers_gate_through_check_db_exposed(self, db_mod):
        from odoo.exceptions import AccessDenied

        gated = db_mod.rpc._REQUIRES_MASTER_PASSWORD - self._ALLOWLIST_EXEMPT
        assert set(self._UNEXPOSED_CALL) == gated, (
            f"the call recipes below no longer match the dispatch table "
            f"(missing {sorted(gated - set(self._UNEXPOSED_CALL))!r}, stale "
            f"{sorted(set(self._UNEXPOSED_CALL) - gated)!r}).  A new "
            f"master-password handler acting on an existing DB by name needs a "
            f"recipe here — and therefore a real refusal test — or an explicit, "
            f"justified entry in _ALLOWLIST_EXEMPT."
        )

        refusals = {}
        for method, args in self._UNEXPOSED_CALL.items():
            handler = db_mod.rpc._DISPATCH[method]
            with (
                patch.object(db_mod.listing, "list_dbs", return_value=["visible_db"]),
                patch.object(db_mod.lifecycle, "drop_database") as dropped,
                patch("odoo.service.db.dump.subprocess.Popen") as ran,
            ):
                with pytest.raises(Exception) as excinfo:
                    handler(*args)
                refusals[method] = type(excinfo.value)
                assert not dropped.called, f"{method} acted before refusing"
                assert not ran.called, f"{method} shelled out before refusing"

        assert set(refusals.values()) == {AccessDenied}, (
            f"the unexposed-database refusal is not uniform: {refusals!r}. "
            f"Divergent reactions are the original bug — the same hidden name "
            f"produced AccessDenied from exp_dump and 'Database %r was not "
            f"found' from exp_drop, which is itself an existence oracle."
        )


class TestExpDuplicateRollback:
    @pytest.fixture
    def duplicate_env(self, db_mod, tmp_path):
        from contextlib import ExitStack

        fake_db, fake_cr = fake_pg_connection()

        from_fs = tmp_path / "filestore_source"
        from_fs.mkdir()
        (from_fs / "marker.txt").write_text("hello")

        stack = ExitStack()
        stack.enter_context(db_mod.lifecycle.odoo.tools.config.patch(list_db=True))
        stack.enter_context(patch.object(db_mod.lifecycle.odoo.db, "close_db"))
        stack.enter_context(
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db)
        )
        stack.enter_context(
            patch("odoo.service.db.lifecycle.get_database_identifier", return_value="")
        )
        stack.enter_context(patch("odoo.service.db.lifecycle._terminate_backends"))
        stack.enter_context(
            patch.object(
                db_mod.lifecycle.odoo.tools.config,
                "filestore",
                side_effect=lambda name: str(tmp_path / f"filestore_{name}"),
                create=True,
            )
        )
        yield {"cr": fake_cr, "stack": stack, "from_fs": from_fs}
        stack.close()

    def test_drops_db_when_filestore_copy_fails(self, db_mod, duplicate_env):
        fake_registry = MagicMock()
        fake_registry.cursor.return_value = fake_pg_cursor()

        with duplicate_env["stack"]:
            with (
                patch.object(
                    db_mod.lifecycle.odoo.modules.registry.Registry,
                    "new",
                    return_value=fake_registry,
                ),
                patch(
                    "odoo.service.db.lifecycle.odoo.api.Environment",
                    return_value=MagicMock(),
                ),
                patch(
                    "odoo.service.db.lifecycle.shutil.copytree",
                    side_effect=OSError("disk full"),
                ),
                patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            ):
                with pytest.raises(OSError, match="disk full"):
                    db_mod.duplicate_database("source", "newdb")

            mock_drop.assert_called_once_with("newdb")

    def test_drops_db_when_registry_init_fails(self, db_mod, duplicate_env):
        with duplicate_env["stack"]:
            with (
                patch.object(
                    db_mod.lifecycle.odoo.modules.registry.Registry,
                    "new",
                    side_effect=RuntimeError("registry boom"),
                ),
                patch.object(db_mod.lifecycle, "drop_database") as mock_drop,
            ):
                with pytest.raises(RuntimeError, match="registry boom"):
                    db_mod.duplicate_database("source", "newdb")

            mock_drop.assert_called_once_with("newdb")

    def test_drop_failure_does_not_mask_original_error(self, db_mod, duplicate_env):
        with duplicate_env["stack"]:
            with (
                patch.object(
                    db_mod.lifecycle.odoo.modules.registry.Registry,
                    "new",
                    side_effect=RuntimeError("original error"),
                ),
                patch.object(
                    db_mod.lifecycle,
                    "drop_database",
                    side_effect=Exception("drop also failed"),
                ),
            ):
                with pytest.raises(RuntimeError, match="original error"):
                    db_mod.duplicate_database("source", "newdb")


class TestExpRenameRollback:
    @pytest.fixture
    def rename_env(self, db_mod, tmp_path):
        from contextlib import ExitStack

        fake_db, fake_cr = fake_pg_connection()

        old_fs = tmp_path / "filestore_oldname"
        old_fs.mkdir()
        (old_fs / "data.txt").write_text("attachment payload")

        stack = ExitStack()
        stack.enter_context(db_mod.lifecycle.odoo.tools.config.patch(list_db=True))
        stack.enter_context(
            patch.object(db_mod.lifecycle.odoo.modules.registry.Registry, "remove")
        )
        stack.enter_context(patch.object(db_mod.lifecycle.odoo.db, "close_db"))
        stack.enter_context(
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db)
        )
        stack.enter_context(
            patch("odoo.service.db.lifecycle.get_database_identifier", return_value="")
        )
        stack.enter_context(patch("odoo.service.db.lifecycle._terminate_backends"))
        stack.enter_context(
            patch.object(
                db_mod.lifecycle.odoo.tools.config,
                "filestore",
                side_effect=lambda name: str(tmp_path / f"filestore_{name}"),
                create=True,
            )
        )
        yield {"cr": fake_cr, "stack": stack}
        stack.close()

    def test_rolls_back_db_rename_when_filestore_move_fails(self, db_mod, rename_env):
        with rename_env["stack"]:
            with patch(
                "odoo.service.db.lifecycle.shutil.move",
                side_effect=OSError("permission denied"),
            ):
                with pytest.raises(RuntimeError, match="permission denied"):
                    db_mod.rename_database("oldname", "newname")

        rename_calls = [
            c
            for c in rename_env["cr"].execute.call_args_list
            if "ALTER DATABASE" in str(c)
        ]
        assert len(rename_calls) == 2, (
            f"Expected 2 ALTER DATABASE RENAME calls (forward + rollback), "
            f"got {len(rename_calls)}: {rename_calls}"
        )

    def test_double_failure_surfaces_both_errors(self, db_mod, rename_env):
        rename_call_count = 0

        def execute_side_effect(sql, *args, **kwargs):
            nonlocal rename_call_count
            if "ALTER DATABASE" in str(sql):
                rename_call_count += 1
                if rename_call_count == 2:
                    raise RuntimeError("rollback rename also failed")

        rename_env["cr"].execute.side_effect = execute_side_effect

        with rename_env["stack"]:
            with patch(
                "odoo.service.db.lifecycle.shutil.move",
                side_effect=OSError("disk full"),
            ):
                with pytest.raises(RuntimeError, match="manual intervention required"):
                    db_mod.rename_database("oldname", "newname")


class TestDropDatabaseRetryBudget:
    def test_retry_count_is_at_least_5(self, db_mod):
        assert db_mod.lifecycle._DROP_DATABASE_MAX_RETRIES >= 5, (
            "Lowering the retry count below 5 reintroduces the 'connection "
            "lands in the drop window' failure mode under load."
        )

    def test_backoff_is_exponential(self, db_mod):
        base = db_mod.lifecycle._DROP_DATABASE_BACKOFF_BASE
        delays = [
            base * (2 ** (n - 1))
            for n in range(1, db_mod.lifecycle._DROP_DATABASE_MAX_RETRIES + 1)
        ]
        assert all(delays[i] < delays[i + 1] for i in range(len(delays) - 1)), (
            f"Backoff is not strictly increasing: {delays}"
        )
        assert sum(delays) >= 3.0, (
            f"Total backoff budget {sum(delays):.2f}s is too short for a busy DB"
        )


class TestExpListNoRedundantCheck:
    def test_passthrough_when_list_db_enabled(self, db_mod):
        with patch.object(
            db_mod.listing, "list_dbs", return_value=["a", "b"]
        ) as mock_list:
            assert db_mod.exp_list() == ["a", "b"]
        mock_list.assert_called_once_with()

    def test_propagates_access_denied_from_list_dbs(self, db_mod):
        from odoo.exceptions import AccessDenied

        with patch.object(db_mod.listing, "list_dbs", side_effect=AccessDenied):
            with pytest.raises(AccessDenied):
                db_mod.exp_list()

    def test_document_kwarg_accepted_for_backcompat(self, db_mod):
        with patch.object(db_mod.listing, "list_dbs", return_value=[]):
            assert db_mod.exp_list() == []
            assert db_mod.exp_list(document=True) == []


class TestDropConnLogging:
    def test_failure_is_logged_at_debug(self, db_mod, caplog):
        import logging

        fake_cr = MagicMock()
        fake_cr.execute.side_effect = RuntimeError(
            "permission denied for pg_signal_backend"
        )

        target_logger = logging.getLogger("odoo.service.db")
        prior_level = target_logger.level
        target_logger.setLevel(logging.DEBUG)
        try:
            with caplog.at_level(logging.DEBUG, logger="odoo.service.db"):
                db_mod.lifecycle._terminate_backends(fake_cr, "any_db")
        finally:
            target_logger.setLevel(prior_level)

        assert any(
            "pg_terminate_backend failed" in r.message
            for r in caplog.records
            if r.name == "odoo.service.db"
        ), (
            f"Expected debug log; got records: {[(r.name, r.message) for r in caplog.records]}"
        )

    def test_failure_does_not_propagate(self, db_mod):
        fake_cr = MagicMock()
        fake_cr.execute.side_effect = RuntimeError("anything")
        db_mod.lifecycle._terminate_backends(fake_cr, "any_db")


class TestRestoreDbOnErrorStop:
    def test_psql_invocation_passes_on_error_stop(
        self, db_mod, bypass_db_mgmt, zip_dump
    ):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=False),
            patch.object(db_mod.restore, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "drop_database"),
            patch(
                "odoo.service.db.restore.subprocess.run",
                return_value=CompletedProcess(args=[], returncode=1, stderr="x"),
            ) as mock_run,
        ):
            with pytest.raises(RuntimeError):
                db_mod.restore_db("newdb", zip_dump)

        cmd = mock_run.call_args.args[0]
        assert "-v" in cmd and "ON_ERROR_STOP=1" in cmd, (
            f"psql restore must pass -v ON_ERROR_STOP=1; got {cmd!r}"
        )
        assert cmd[cmd.index("-v") + 1] == "ON_ERROR_STOP=1", (
            f"-v must be immediately followed by ON_ERROR_STOP=1; got {cmd!r}"
        )


class TestRestoreDbNameValidation:
    def test_rejects_overlong_name_before_any_side_effect(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.restore, "exp_db_exist") as mock_exist,
            patch.object(db_mod.restore, "_create_empty_database") as mock_create,
        ):
            with pytest.raises(ValueError, match="63 characters"):
                db_mod.restore_db("a" * 70, "/dev/null")
        mock_exist.assert_not_called()
        mock_create.assert_not_called()

    def test_rejects_invalid_shape_before_any_side_effect(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.restore, "exp_db_exist") as mock_exist,
            patch.object(db_mod.restore, "_create_empty_database") as mock_create,
        ):
            with pytest.raises(ValueError, match="must start with"):
                db_mod.restore_db("../etc/passwd", "/dev/null")
        mock_exist.assert_not_called()
        mock_create.assert_not_called()

    def test_valid_name_passes_validation(self, db_mod, bypass_db_mgmt):
        with (
            patch.object(db_mod.restore, "exp_db_exist", return_value=True),
            patch.object(db_mod.restore, "_create_empty_database"),
        ):
            with pytest.raises(RuntimeError, match="already exists"):
                db_mod.restore_db("valid_db.name-1", "/dev/null")


class TestRetryTerminateThenDdl:
    def test_returns_on_first_success(self, db_mod):
        cr = MagicMock()
        run = MagicMock()
        with (
            patch.object(db_mod.lifecycle, "_terminate_backends") as drop_conn,
            patch("odoo.service.db.lifecycle.time.sleep"),
        ):
            db_mod.lifecycle._retry_terminate_then_ddl(cr, "db", "OP: db", run)
        run.assert_called_once()
        drop_conn.assert_called_once_with(cr, "db")

    def test_retries_on_object_in_use_then_succeeds(self, db_mod):
        import psycopg

        cr = MagicMock()
        run = MagicMock(side_effect=[psycopg.errors.ObjectInUse("busy"), None])
        with (
            patch.object(db_mod.lifecycle, "_terminate_backends") as drop_conn,
            patch("odoo.service.db.lifecycle.time.sleep") as sleep,
        ):
            db_mod.lifecycle._retry_terminate_then_ddl(cr, "db", "OP: db", run)
        assert run.call_count == 2
        assert drop_conn.call_count == 2
        sleep.assert_called_once()

    def test_exhaustion_raises_runtimeerror_with_last_error(self, db_mod):
        import psycopg

        cr = MagicMock()
        run = MagicMock(side_effect=psycopg.errors.ObjectInUse("forever"))
        with (
            patch.object(db_mod.lifecycle, "_terminate_backends"),
            patch("odoo.service.db.lifecycle.time.sleep"),
        ):
            with pytest.raises(RuntimeError, match="forever"):
                db_mod.lifecycle._retry_terminate_then_ddl(cr, "db", "OP: db", run)
        assert run.call_count == db_mod.lifecycle._DROP_DATABASE_MAX_RETRIES

    def test_non_object_in_use_propagates_without_retry(self, db_mod):
        cr = MagicMock()
        run = MagicMock(side_effect=ValueError("hard fail"))
        with (
            patch.object(db_mod.lifecycle, "_terminate_backends"),
            patch("odoo.service.db.lifecycle.time.sleep") as sleep,
        ):
            with pytest.raises(ValueError, match="hard fail"):
                db_mod.lifecycle._retry_terminate_then_ddl(cr, "db", "OP: db", run)
        run.assert_called_once()
        sleep.assert_not_called()

    def test_no_sleep_after_final_attempt(self, db_mod):
        import psycopg

        cr = MagicMock()
        run = MagicMock(side_effect=psycopg.errors.ObjectInUse("forever"))
        with (
            patch.object(db_mod.lifecycle, "_terminate_backends"),
            patch("odoo.service.db.lifecycle.time.sleep") as sleep,
        ):
            with pytest.raises(RuntimeError):
                db_mod.lifecycle._retry_terminate_then_ddl(cr, "db", "OP: db", run)
        assert run.call_count == db_mod.lifecycle._DROP_DATABASE_MAX_RETRIES
        assert sleep.call_count == db_mod.lifecycle._DROP_DATABASE_MAX_RETRIES - 1


class TestRestoreArchiveExpansionBound:
    def _bomb(self, tmp_path, mb):
        path = tmp_path / "bomb.zip"
        blob = b"A" * (1024 * 1024)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            with z.open("dump.sql", "w") as fh:
                for _ in range(mb):
                    fh.write(blob)
        return path

    def test_budget_scales_with_compressed_size_but_has_a_floor(self, db_mod, tmp_path):
        small = tmp_path / "small.zip"
        small.write_bytes(b"x" * 1024)
        assert (
            db_mod.restore._unpack_budget(str(small))
            == db_mod.restore._RESTORE_MIN_UNPACKED_BYTES
        )
        big = tmp_path / "big.zip"
        big.write_bytes(b"x" * (50 * 1024 * 1024))
        assert db_mod.restore._unpack_budget(str(big)) == (
            50 * 1024 * 1024 * db_mod.restore._RESTORE_MAX_EXPANSION_RATIO
        )

    def test_extraction_stops_at_the_budget(self, db_mod, tmp_path):
        path = self._bomb(tmp_path, 24)
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(path) as z:
            with pytest.raises(RuntimeError, match="expands to more than"):
                db_mod.restore._extract_members_bounded(
                    z, ["dump.sql"], str(dest), 8 * 1024 * 1024
                )

    def test_counts_bytes_produced_not_the_declared_header_size(self, db_mod, tmp_path):
        path = self._bomb(tmp_path, 40)
        with zipfile.ZipFile(path, "a") as z:
            z.getinfo("dump.sql").file_size = 1
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(path) as z:
            with pytest.raises(RuntimeError, match="expands to more than"):
                db_mod.restore._extract_members_bounded(
                    z, ["dump.sql"], str(dest), 4 * 1024 * 1024
                )

    def test_nested_members_land_intact_within_budget(self, db_mod, tmp_path):
        path = tmp_path / "ok.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("dump.sql", "SELECT 1;\n")
            z.writestr("filestore/27/27c0abc", b"payload-a")
            z.writestr("filestore/3d/3daebe", b"payload-b")
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(path) as z:
            written = db_mod.restore._extract_members_bounded(
                z,
                ["dump.sql", "filestore/27/27c0abc", "filestore/3d/3daebe"],
                str(dest),
                10 * 1024 * 1024,
            )
        assert (dest / "filestore/27/27c0abc").read_bytes() == b"payload-a"
        assert (dest / "filestore/3d/3daebe").read_bytes() == b"payload-b"
        assert written == len("SELECT 1;\n") + len(b"payload-a") + len(b"payload-b")


class TestDatabaseIdentifierPercent:
    def test_percent_in_identifier_does_not_raise(self, db_mod):
        cr = MagicMock()
        cr.connection = None
        sql = db_mod.get_database_identifier(cr, "weird%name")
        assert (sql.code % sql.params) == '"weird%name"'


class TestDatabaseDdlSetsAutocommitFirst:
    @staticmethod
    def _recorder():
        connections = []

        def db_connect(_name, **_kwargs):
            events = []
            cr = MagicMock()
            connection = MagicMock()
            type(connection).autocommit = property(
                lambda _self: True,
                lambda _self, value, _e=events: _e.append(("autocommit", value)),
            )
            cr.connection = connection
            cr.execute.side_effect = lambda sql, *a, **kw: events.append(
                ("execute", str(sql)[:40])
            )
            cr.fetchone.return_value = (1,)
            cr.fetchall.return_value = []
            cr.__enter__ = MagicMock(return_value=cr)
            cr.__exit__ = MagicMock(return_value=False)
            conn = MagicMock()
            conn.cursor.return_value = cr
            connections.append(events)
            return conn

        return db_connect, connections

    _DATABASE_DDL = ("CREATE DATABASE", "DROP DATABASE", "ALTER DATABASE")

    @classmethod
    def _assert_every_statement_follows_autocommit(cls, connections, verb):
        issuing = [
            e
            for e in connections
            if any(
                kind == "execute" and any(d in sql.upper() for d in cls._DATABASE_DDL)
                for kind, sql in e
            )
        ]
        assert issuing, (
            f"{verb} issued no database-level DDL on any connection; either it "
            f"stopped doing so or this test no longer drives it. "
            f"Connections: {connections}"
        )
        for events in issuing:
            assert ("autocommit", True) in events, (
                f"{verb} issued SQL on a connection whose autocommit it never "
                f"set; PostgreSQL refuses database DDL inside the transaction "
                f"psycopg opens implicitly. Events: {events}"
            )
            first_autocommit = events.index(("autocommit", True))
            first_execute = next(
                i for i, (kind, _) in enumerate(events) if kind == "execute"
            )
            assert first_autocommit < first_execute, (
                f"{verb} issued a statement before setting autocommit, which "
                f"opens the very transaction the flag avoids. Events: {events}"
            )

    def test_create_empty_database(self, db_mod, bypass_db_mgmt):
        import odoo.tools

        db_connect, connections = self._recorder()
        with (
            patch.object(
                odoo.tools,
                "config",
                _MockConfig(
                    {"list_db": True, "db_template": "template0", "unaccent": False}
                ),
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", db_connect),
            patch(
                "odoo.service.db.lifecycle.get_database_identifier", return_value="x"
            ),
            patch("odoo.service.db.lifecycle._create_faketime_now_function"),
        ):
            db_mod._create_empty_database("newdb")
        self._assert_every_statement_follows_autocommit(
            connections, "_create_empty_database"
        )

    def test_duplicate_database(self, db_mod, bypass_db_mgmt):
        import odoo.tools

        db_connect, connections = self._recorder()
        with (
            patch.object(
                odoo.tools,
                "config",
                _MockConfig(
                    {"list_db": True, "unaccent": False, "db_template": "template0"}
                ),
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", db_connect),
            patch(
                "odoo.service.db.lifecycle.get_database_identifier", return_value="x"
            ),
            patch.object(
                db_mod.lifecycle.odoo.modules.registry.Registry, "clear_database_state"
            ),
            patch.object(db_mod.lifecycle.odoo.db, "close_db"),
            patch.object(db_mod.lifecycle, "_terminate_backends"),
            patch.object(db_mod.lifecycle, "_check_filestore_dest_free"),
            patch.object(db_mod.lifecycle.shutil, "copytree"),
        ):
            with contextlib.suppress(Exception):
                db_mod.duplicate_database("src", "dst")
        self._assert_every_statement_follows_autocommit(
            connections, "duplicate_database"
        )

    def test_drop_database(self, db_mod, bypass_db_mgmt):
        db_connect, connections = self._recorder()
        with (
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", db_connect),
            patch(
                "odoo.service.db.lifecycle.get_database_identifier", return_value="x"
            ),
            patch.object(
                db_mod.lifecycle.odoo.modules.registry.Registry, "clear_database_state"
            ),
            patch.object(db_mod.lifecycle.odoo.db, "close_db"),
            patch.object(db_mod.lifecycle, "_terminate_backends"),
        ):
            db_mod.drop_database("victim")
        assert (
            len([e for e in connections if any(k == "execute" for k, _ in e)]) >= 2
        ), (
            "expected the probe AND the drop to issue SQL on separate connections; "
            "if that changed, this test no longer covers both autocommit sites"
        )
        self._assert_every_statement_follows_autocommit(connections, "drop_database")

    def test_rename_database(self, db_mod, bypass_db_mgmt):
        db_connect, connections = self._recorder()
        with (
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", db_connect),
            patch(
                "odoo.service.db.lifecycle.get_database_identifier", return_value="x"
            ),
            patch.object(
                db_mod.lifecycle.odoo.modules.registry.Registry, "clear_database_state"
            ),
            patch.object(db_mod.lifecycle.odoo.db, "close_db"),
            patch.object(db_mod.lifecycle, "_terminate_backends"),
            patch.object(db_mod.lifecycle.shutil, "move"),
        ):
            db_mod.rename_database("old_name", "new_name")
        self._assert_every_statement_follows_autocommit(connections, "rename_database")


class TestCreateEmptyDatabaseHardening:
    def _mock_pg(self, db_mod, *, create_raises=None):
        import odoo.db

        cr = MagicMock()
        cr.connection = MagicMock()
        if create_raises is not None:
            cr.execute.side_effect = create_raises
        conn = MagicMock()
        conn.cursor.return_value = cr
        return patch.object(odoo.db, "db_connect", return_value=conn), conn, cr

    @pytest.mark.parametrize("template", ["template0", "tpl_custom"])
    def test_the_new_database_is_created_from_the_template_not_vice_versa(
        self, db_mod, bypass_db_mgmt, template
    ):
        import odoo.tools

        seen: list[str] = []

        def identifier(_cr, name):
            seen.append(name)
            return name

        fake_db, _fake_cr = fake_pg_connection()
        with (
            patch.object(
                odoo.tools,
                "config",
                _MockConfig(
                    {"list_db": True, "db_template": template, "unaccent": False}
                ),
            ),
            patch("odoo.service.db.lifecycle.odoo.db.db_connect", return_value=fake_db),
            patch("odoo.service.db.lifecycle.get_database_identifier", identifier),
            patch("odoo.service.db.lifecycle._create_faketime_now_function"),
        ):
            db_mod._create_empty_database("newdb")

        assert seen[:2] == ["newdb", template], (
            f"CREATE DATABASE quoted {seen[:2]}; the new database must come "
            f"first and the template second, or a create silently targets the "
            f"template (or clones the wrong source)"
        )

    def test_rejects_malformed_db_template(self, db_mod, bypass_db_mgmt):
        cm, _conn, _cr = self._mock_pg(db_mod)
        with cm:
            with pytest.raises(ValueError, match="Invalid database name"):
                db_mod._create_empty_database("newdb", template="bad%name")

    def test_setup_if_exists_false_skips_setup_on_collision(
        self, db_mod, bypass_db_mgmt
    ):
        import psycopg

        from odoo.tools import SQL

        cm, _conn, _cr = self._mock_pg(
            db_mod, create_raises=psycopg.errors.DuplicateDatabase("exists")
        )
        with (
            cm as db_connect_mock,
            patch.object(
                db_mod.lifecycle, "get_database_identifier", return_value=SQL("x")
            ),
        ):
            with pytest.raises(db_mod.DatabaseExists):
                db_mod._create_empty_database(
                    "taken", template="template0", setup_if_exists=False
                )
        assert db_connect_mock.call_args_list == [call("postgres")]


class TestRpcDbExistGate:
    def _cfg(self, **over):
        # dbfilter/db_name decide which of list_dbs' two sources answers, and
        # therefore whether the listing is proof of existence on its own.
        cfg = _MockConfig(
            {
                "list_db": True,
                "db_template": "template1",
                "dbfilter": "",
                "db_name": [],
            }
        )
        cfg.update(over)
        return cfg

    def test_dispatch_uses_the_gated_wrapper(self, db_mod):
        assert db_mod.rpc._DISPATCH["db_exist"] is db_mod.listing._rpc_db_exist
        assert db_mod.rpc._DISPATCH["db_exist"] is not db_mod.exp_db_exist

    def test_list_db_false_answers_false_for_everything(self, db_mod):
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", self._cfg(list_db=False)),
            patch.object(db_mod.listing, "list_dbs", return_value=["served"]),
            patch.object(db_mod.listing, "exp_db_exist", return_value=True) as inner,
        ):
            assert db_mod.listing._rpc_db_exist("served") is False
            assert db_mod.listing._rpc_db_exist("nope") is False
        inner.assert_not_called()

    def test_unexposed_existing_db_answers_false_without_connecting(self, db_mod):
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", self._cfg()),
            patch.object(db_mod.listing, "list_dbs", return_value=["served"]),
            patch.object(db_mod.listing, "exp_db_exist") as inner,
        ):
            assert db_mod.listing._rpc_db_exist("other_tenant_db") is False
        inner.assert_not_called()

    def test_an_exposed_db_from_the_catalogue_answers_without_connecting(self, db_mod):
        """The catalogue already proved existence; a connection re-proves it.

        This asserted `exp_db_exist` WAS called, which was the old contract.
        Measured at 50 calls, that connection cost 21.2ms and 50 pool borrows
        against 0.2ms and 0 for the listing alone -- and for a database this
        process has not touched it is a connectability probe plus a
        three-thread pool build, on the one call every client makes at connect.
        """
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", self._cfg()),
            patch.object(db_mod.listing, "list_dbs", return_value=["served"]),
            patch.object(db_mod.listing, "exp_db_exist", return_value=True) as inner,
        ):
            assert db_mod.listing._rpc_db_exist("served") is True
        inner.assert_not_called()

    def test_an_exposed_db_from_db_name_still_connects(self, db_mod):
        """`db_name` is a list of names an operator asked us to serve.

        It is not evidence any of them was created, so this branch keeps
        paying for the connection -- otherwise `db_exist` answers True for
        every configured name whether the database exists or not.
        """
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", self._cfg(db_name=["served"])),
            patch.object(db_mod.listing, "exp_db_exist", return_value=False) as inner,
        ):
            assert db_mod.listing._rpc_db_exist("served") is False
        inner.assert_called_once_with("served")

    @pytest.mark.parametrize("name", ["postgres", "template0", "template1"])
    def test_system_and_template_dbs_are_never_disclosed(self, db_mod, name):
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", self._cfg()),
            patch.object(db_mod.listing, "list_dbs", return_value=[name]),
            patch.object(db_mod.listing, "exp_db_exist") as inner,
        ):
            assert db_mod.listing._rpc_db_exist(name) is False
        inner.assert_not_called()

    @pytest.mark.parametrize("name", ["", "-leading", "a" * 64, "sp ace", "semi;colon"])
    def test_malformed_names_are_rejected_before_pg(self, db_mod, name):
        import odoo.tools

        with (
            patch.object(odoo.tools, "config", self._cfg()),
            patch.object(db_mod.listing, "list_dbs") as listed,
            patch.object(db_mod.listing, "exp_db_exist") as inner,
        ):
            assert db_mod.listing._rpc_db_exist(name) is False
        listed.assert_not_called()
        inner.assert_not_called()


class TestListDbIncompatiblePoolSideEffects:
    @pytest.fixture
    def probe(self, db_mod):
        def _run(compat: dict, preexisting: set):
            import odoo

            closed = []
            cur = MagicMock()
            cur.__enter__ = lambda s: s
            cur.__exit__ = lambda s, *a: False

            def fake_table_exists(cr, table):
                return compat[cr._dbname] is not None

            def fake_connect(name):
                conn = MagicMock()
                c = MagicMock()
                c._dbname = name
                c.fetchone.return_value = (compat[name],) if compat[name] else None
                conn.cursor.return_value = c
                return conn

            with (
                patch.object(odoo.db, "db_connect", side_effect=fake_connect),
                patch.object(
                    odoo.db, "is_pooled", side_effect=lambda n: n in preexisting
                ),
                patch.object(odoo.db, "close_db", side_effect=closed.append),
                patch.object(
                    odoo.db.schema, "table_exists", side_effect=fake_table_exists
                ),
                patch.object(
                    db_mod.listing, "version_info", (19, 0, 0, "final", 0, "")
                ),
            ):
                incompatible = db_mod.list_db_incompatible(list(compat))
            return incompatible, closed

        return _run

    def test_compatible_preexisting_pool_survives(self, probe):
        incompatible, closed = probe({"live": "19.0.1.0"}, preexisting={"live"})
        assert incompatible == []
        assert closed == [], (
            "list_db_incompatible evicted the pool of a healthy, already-pooled "
            "database — the unauthenticated pool-churn regression"
        )

    def test_compatible_pool_we_opened_is_closed(self, probe):
        incompatible, closed = probe({"idle": "19.0.1.0"}, preexisting=set())
        assert incompatible == []
        assert closed == ["idle"]

    def test_incompatible_is_always_closed(self, probe):
        incompatible, closed = probe({"old": "18.0.1.0"}, preexisting={"old"})
        assert incompatible == ["old"]
        assert closed == ["old"]

    def test_mixed_set_closes_only_the_right_ones(self, probe):
        incompatible, closed = probe(
            {"live": "19.0.1.0", "old": "18.0.1.0", "idle": "19.0.1.0"},
            preexisting={"live", "old"},
        )
        assert incompatible == ["old"]
        assert sorted(closed) == ["idle", "old"]


class TestRetryOnObjectInUse:
    def test_retries_then_succeeds(self, db_mod):
        import psycopg

        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise psycopg.errors.ObjectInUse("still in use")

        with patch.object(db_mod.lifecycle.time, "sleep"):
            db_mod.lifecycle._retry_on_object_in_use("TEST OP", flaky)
        assert len(calls) == 3

    def test_gives_up_as_runtimeerror_naming_the_op(self, db_mod):
        import psycopg

        def always():
            raise psycopg.errors.ObjectInUse("source database is being accessed")

        with (
            patch.object(db_mod.lifecycle.time, "sleep"),
            pytest.raises(RuntimeError) as exc,
        ):
            db_mod.lifecycle._retry_on_object_in_use(
                "CREATE DB: x (template t)", always
            )
        assert "CREATE DB: x (template t)" in str(exc.value)
        assert "still in use after" in str(exc.value)

    def test_other_errors_abort_immediately(self, db_mod):
        def boom():
            raise ValueError("unrelated")

        with pytest.raises(ValueError):
            db_mod.lifecycle._retry_on_object_in_use("TEST OP", boom)

    def test_before_attempt_runs_once_per_try(self, db_mod):
        import psycopg

        before = []
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise psycopg.errors.ObjectInUse("busy")

        with patch.object(db_mod.lifecycle.time, "sleep"):
            db_mod.lifecycle._retry_on_object_in_use(
                "TEST OP", flaky, before_attempt=lambda: before.append(1)
            )
        assert len(before) == 3

    def test_terminate_variant_still_evicts_each_attempt(self, db_mod):
        import psycopg

        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise psycopg.errors.ObjectInUse("busy")

        cr = MagicMock()
        with (
            patch.object(db_mod.lifecycle, "_terminate_backends") as drop_conn,
            patch.object(db_mod.lifecycle.time, "sleep"),
        ):
            db_mod.lifecycle._retry_terminate_then_ddl(
                cr, "target", "DROP DB: target", flaky
            )
        assert drop_conn.call_count == 2


class TestCreateEmptyDatabaseTemplateContention:
    def test_create_retries_object_in_use(self, db_mod, bypass_db_mgmt):
        import psycopg

        attempts = []

        def execute(sql, *a, **kw):
            text = str(sql)
            if "CREATE DATABASE" in text:
                attempts.append(1)
                if len(attempts) < 3:
                    raise psycopg.errors.ObjectInUse(
                        'source database "tpl" is being accessed by other users'
                    )

        conn, _cr = fake_pg_connection(execute=execute)

        import odoo

        with (
            patch.object(odoo.db, "db_connect", return_value=conn),
            patch.object(
                db_mod.lifecycle, "get_database_identifier", side_effect=lambda c, n: n
            ),
            patch.object(db_mod.lifecycle, "_create_faketime_now_function"),
            patch.object(db_mod.lifecycle.time, "sleep"),
            patch.object(
                odoo.tools,
                "config",
                _MockConfig({"list_db": True, "db_template": "tpl", "unaccent": False}),
            ),
        ):
            db_mod._create_empty_database("newdb", setup_if_exists=False)
        assert len(attempts) == 3, "CREATE DATABASE was not retried on ObjectInUse"

    def test_create_does_not_terminate_template_sessions(self, db_mod, bypass_db_mgmt):
        import odoo

        conn, _cr = fake_pg_connection()

        with (
            patch.object(odoo.db, "db_connect", return_value=conn),
            patch.object(
                db_mod.lifecycle, "get_database_identifier", side_effect=lambda c, n: n
            ),
            patch.object(db_mod.lifecycle, "_create_faketime_now_function"),
            patch.object(db_mod.lifecycle, "_terminate_backends") as drop_conn,
            patch.object(
                odoo.tools,
                "config",
                _MockConfig({"list_db": True, "db_template": "tpl", "unaccent": False}),
            ),
        ):
            db_mod._create_empty_database("newdb", setup_if_exists=False)
        drop_conn.assert_not_called()


class TestZipDumpDoesNotStageFilestore:
    @pytest.fixture
    def live_filestore(self, tmp_path):
        fs = tmp_path / "filestore" / "db"
        (fs / "aa").mkdir(parents=True)
        (fs / "aa" / "blob1").write_bytes(b"x" * 1024)
        (fs / "aa" / "blob2").write_bytes(b"y" * 1024)
        return fs

    def _dump(self, db_mod, filestore, stream, with_filestore=True):
        import odoo

        class _Cfg(_MockConfig):
            def filestore(self, name):
                return str(filestore)

        def fake_pg_dump(cmd, env, out):
            out.write(b"-- SQL DUMP\nSELECT 1;\n")

        with (
            patch.object(odoo.tools, "config", _Cfg({"list_db": True})),
            patch.object(db_mod.dump, "get_pg_tool_path", return_value="/bin/true"),
            patch.object(db_mod.dump, "exec_pg_environ", return_value={}),
            patch.object(
                db_mod.dump, "dump_db_manifest", return_value={"odoo_dump": "1"}
            ),
            patch.object(db_mod.dump, "_run_pg_dump", side_effect=fake_pg_dump),
            patch.object(odoo.db, "db_connect"),
            patch.object(db_mod.dump.shutil, "copytree") as copytree,
        ):
            db_mod.dump_db("db", stream, "zip", with_filestore)
        return copytree

    def test_no_copytree_and_archive_is_complete(self, db_mod, live_filestore):
        buf = io.BytesIO()
        copytree = self._dump(db_mod, live_filestore, buf)
        copytree.assert_not_called()

        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            names = set(z.namelist())
            assert "dump.sql" in names
            assert "manifest.json" in names
            assert {"filestore/aa/blob1", "filestore/aa/blob2"} <= names
            assert z.read("dump.sql") == b"-- SQL DUMP\nSELECT 1;\n"
            assert z.read("filestore/aa/blob1") == b"x" * 1024

    def test_without_filestore_only_sql_and_manifest(self, db_mod, live_filestore):
        buf = io.BytesIO()
        self._dump(db_mod, live_filestore, buf, with_filestore=False)
        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            assert set(z.namelist()) == {"manifest.json", "dump.sql"}

    def test_sql_precedes_filestore_in_the_archive(self, db_mod, live_filestore):
        buf = io.BytesIO()
        self._dump(db_mod, live_filestore, buf)
        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            order = z.namelist()
        assert order.index("dump.sql") < min(
            i for i, n in enumerate(order) if n.startswith("filestore/")
        )

    def test_symlink_escaping_the_filestore_is_skipped(
        self, db_mod, live_filestore, tmp_path
    ):
        secret = tmp_path / "secret.txt"
        secret.write_text("do not back me up")
        (live_filestore / "aa" / "escape").symlink_to(secret)

        buf = io.BytesIO()
        self._dump(db_mod, live_filestore, buf)
        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            assert "filestore/aa/escape" not in z.namelist()
            assert b"do not back me up" not in b"".join(z.read(n) for n in z.namelist())

    def test_stream_none_returns_seekable_archive(self, db_mod, live_filestore):
        import odoo

        class _Cfg(_MockConfig):
            def filestore(self, name):
                return str(live_filestore)

        def fake_pg_dump(cmd, env, out):
            out.write(b"SELECT 1;\n")

        with (
            patch.object(odoo.tools, "config", _Cfg({"list_db": True})),
            patch.object(db_mod.dump, "get_pg_tool_path", return_value="/bin/true"),
            patch.object(db_mod.dump, "exec_pg_environ", return_value={}),
            patch.object(
                db_mod.dump, "dump_db_manifest", return_value={"odoo_dump": "1"}
            ),
            patch.object(db_mod.dump, "_run_pg_dump", side_effect=fake_pg_dump),
            patch.object(odoo.db, "db_connect"),
        ):
            fh = db_mod.dump_db("db", None, "zip")
        try:
            assert fh.tell() == 0
            with zipfile.ZipFile(fh) as z:
                assert "dump.sql" in z.namelist()
        finally:
            fh.close()


class TestPublicReadVerbsAreMemoized:
    def test_countries_xml_parsed_once(self, db_mod):
        db_mod.listing._read_countries.cache_clear()
        try:
            with patch.object(
                db_mod.listing.ET, "parse", wraps=db_mod.listing.ET.parse
            ) as parse:
                first = db_mod.exp_list_countries()
                second = db_mod.exp_list_countries()
            assert parse.call_count == 1, "the country XML was re-parsed per call"
            assert first == second
        finally:
            db_mod.listing._read_countries.cache_clear()

    def test_countries_result_is_not_shared_across_calls(self, db_mod):
        db_mod.listing._read_countries.cache_clear()
        try:
            first = db_mod.exp_list_countries()
            first.append(["zz", "Mutated"])
            first[0][0] = "hacked"
            second = db_mod.exp_list_countries()
            assert ["zz", "Mutated"] not in second
            assert second[0][0] != "hacked"
        finally:
            db_mod.listing._read_countries.cache_clear()

    def test_countries_shape_is_list_of_lists(self, db_mod):
        result = db_mod.exp_list_countries()
        assert isinstance(result, list)
        assert all(isinstance(row, list) and len(row) == 2 for row in result)

    def test_languages_csv_read_once(self):
        from odoo.tools import locale_utils

        locale_utils._read_lang_csv.cache_clear()
        try:
            with patch.object(
                locale_utils, "file_open", wraps=locale_utils.file_open
            ) as fo:
                first = locale_utils.get_languages()
                second = locale_utils.get_languages()
            assert fo.call_count == 1, "res.lang.csv was re-read per call"
            assert first == second
            assert isinstance(first, list)
        finally:
            locale_utils._read_lang_csv.cache_clear()

    def test_languages_result_is_not_shared_across_calls(self):
        from odoo.tools import locale_utils

        locale_utils._read_lang_csv.cache_clear()
        try:
            first = locale_utils.get_languages()
            first.append(("zz_ZZ", "Mutated"))
            assert ("zz_ZZ", "Mutated") not in locale_utils.get_languages()
        finally:
            locale_utils._read_lang_csv.cache_clear()

    def test_language_read_failure_is_not_cached(self):
        from odoo.tools import locale_utils

        locale_utils._read_lang_csv.cache_clear()
        try:
            with patch.object(locale_utils, "file_open", side_effect=OSError("EIO")):
                degraded = locale_utils.get_languages()
            assert degraded == [("en_US", "English")]

            recovered = locale_utils.get_languages()
            assert len(recovered) > 1, (
                "a transient res.lang.csv failure was cached as the permanent answer"
            )
        finally:
            locale_utils._read_lang_csv.cache_clear()


class TestExpDropGate:
    def _patched(self, db_mod, exposed, dropped=True):
        import odoo

        return [
            patch.object(odoo.tools, "config", _MockConfig({"list_db": True})),
            patch.object(db_mod.listing, "list_dbs", return_value=exposed),
            patch.object(db_mod.lifecycle, "drop_database", return_value=dropped),
        ]

    def test_unexposed_database_raises_access_denied(self, db_mod):
        from odoo.exceptions import AccessDenied

        with ExitStack() as stack:
            for p in self._patched(db_mod, ["visible"]):
                stack.enter_context(p)
            with pytest.raises(AccessDenied):
                db_mod.exp_drop("hidden")

    def test_unexposed_database_is_never_actually_dropped(self, db_mod):
        from odoo.exceptions import AccessDenied

        with ExitStack() as stack:
            for p in self._patched(db_mod, ["visible"])[:-1]:
                stack.enter_context(p)
            drop = stack.enter_context(patch.object(db_mod.lifecycle, "drop_database"))
            with pytest.raises(AccessDenied):
                db_mod.exp_drop("hidden")
        drop.assert_not_called()

    def test_false_now_means_only_that_the_database_was_absent(self, db_mod):
        with ExitStack() as stack:
            for p in self._patched(db_mod, ["gone"], dropped=False):
                stack.enter_context(p)
            assert db_mod.exp_drop("gone") is False

    def test_exposed_and_present_returns_true(self, db_mod):
        with ExitStack() as stack:
            for p in self._patched(db_mod, ["live"], dropped=True):
                stack.enter_context(p)
            assert db_mod.exp_drop("live") is True

    def test_gate_matches_its_siblings_exactly(self, db_mod):
        from odoo.exceptions import AccessDenied

        with ExitStack() as stack:
            for p in self._patched(db_mod, ["visible"]):
                stack.enter_context(p)
            stack.enter_context(patch.object(db_mod.lifecycle, "rename_database"))
            for call in (
                lambda: db_mod.exp_drop("hidden"),
                lambda: db_mod.exp_rename("hidden", "other"),
            ):
                with pytest.raises(AccessDenied):
                    call()


class TestUnpackBudgetAcceptsFileObjects:
    def test_path_sizing_unchanged(self, db_mod, zip_dump):
        expected = pathlib.Path(zip_dump).stat().st_size
        assert db_mod.restore._get_source_size(zip_dump) == expected

    def test_spooled_temporary_file_is_sized_without_a_path(self, db_mod):
        import io as _io

        buf = _io.BytesIO(b"0123456789")
        assert db_mod.restore._get_source_size(buf) == 10
        assert buf.tell() == 0

    def test_spooled_temporary_file_position_is_preserved(self, db_mod):
        sp = tempfile.SpooledTemporaryFile(max_size=1024)  # noqa: SIM115  closed by GC; a `with` would hide the seek assertions below
        sp.write(b"abc" * 100)
        sp.seek(7)
        assert db_mod.restore._get_source_size(sp) == 300
        assert sp.tell() == 7

    def test_unpack_budget_does_not_raise_on_a_file_object(self, db_mod):
        sp = tempfile.SpooledTemporaryFile(max_size=1024)  # noqa: SIM115  as above
        sp.write(b"x" * 2048)
        sp.seek(0)
        budget = db_mod.restore._unpack_budget(sp)
        assert isinstance(budget, int) and budget > 0


class TestPgDumpFailurePolicyIsShared:
    """Two transports, one timeout message and one failure message."""

    def test_both_runners_report_a_timeout_identically(self):
        from odoo.service.db import dump

        assert "ODOO_PG_DUMP_TOTAL_TIMEOUT" in str(dump._prepare_timeout_error(3600.0))
        assert "3600s" in str(dump._prepare_timeout_error(3600.0))

    def test_both_runners_report_a_failure_identically(self):
        from odoo.service.db import dump

        message = str(dump._prepare_pg_dump_failed_error(2, b"  connection refused\n"))
        assert "exit 2" in message
        assert "connection refused" in message

    def test_undecodable_stderr_does_not_mask_the_failure(self):
        from odoo.service.db import dump

        assert "exit 1" in str(dump._prepare_pg_dump_failed_error(1, b"\xff\xfe bad"))

    def test_the_runner_raises_what_the_shared_builder_returns(self):
        from odoo.service.db import dump

        cmd = [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('boom'); sys.exit(3)",
        ]
        marker = RuntimeError("built once, raised as is")
        with patch.object(
            dump, "_prepare_pg_dump_failed_error", return_value=marker
        ) as build:
            with pytest.raises(RuntimeError) as raised:
                dump._run_pg_dump(cmd, dict(os.environ), io.BytesIO())
        assert raised.value is marker
        build.assert_called_once_with(3, b"boom")


class TestANewDatabaseIsAnnouncedToTheListeners:
    """A catalogue-mode cron listener admits an unlisted name only on a notify
    for it; nothing in a fresh database sends one until a job triggers."""

    def test_both_channels_hear_the_name(self, db_mod):
        mock_db, cr = fake_pg_connection()
        with patch("odoo.db.db_connect", return_value=mock_db):
            db_mod.lifecycle._announce_database("newborn")
        assert [c.args for c in cr.execute.call_args_list] == [
            ("SELECT pg_notify(%s, %s)", ("cron_trigger", "newborn")),
            ("SELECT pg_notify(%s, %s)", ("job_queue", "newborn")),
        ]
        assert cr.connection.autocommit is True

    def test_a_failed_announce_does_not_fail_the_creation(self, db_mod):
        with patch("odoo.db.db_connect", side_effect=OSError("postgres away")):
            db_mod.lifecycle._announce_database("newborn")

    @pytest.mark.parametrize(
        ("op", "target"),
        [
            ("exp_create_database", "newborn"),
            ("duplicate_database", "copy"),
            ("rename_database", "renamed"),
        ],
    )
    def test_every_way_a_database_appears_announces_it(
        self, db_mod, bypass_db_mgmt, op, target
    ):
        with (
            patch.object(db_mod.lifecycle, "_announce_database") as announce,
            patch.object(db_mod.lifecycle, "_create_empty_database"),
            patch.object(db_mod.lifecycle, "_check_filestore_dest_free"),
            patch.object(db_mod.lifecycle, "_retry_terminate_then_ddl"),
            patch.object(db_mod.lifecycle, "invalidate_catalog_caches"),
            patch.object(db_mod.lifecycle, "check_db_exposed"),
            patch("odoo.db.close_db"),
            patch("odoo.db.db_connect", return_value=fake_pg_connection()[0]),
            patch("odoo.modules.db.initialize_db"),
            patch("odoo.modules.registry.Registry.clear_database_state"),
            patch("odoo.modules.registry.Registry.new"),
            patch("odoo.api.Environment"),
            patch.object(db_mod.lifecycle.Path, "exists", return_value=False),
        ):
            if op == "exp_create_database":
                db_mod.lifecycle.exp_create_database(target, False, "en_US")
            elif op == "duplicate_database":
                db_mod.lifecycle.duplicate_database("source", target)
            else:
                db_mod.lifecycle.rename_database("source", target)
        announce.assert_called_once_with(target)
