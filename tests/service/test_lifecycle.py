import errno
import logging
import os
import signal
import threading
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _process_state
from odoo.service import settings as server_settings

from .conftest import threaded_server


@pytest.fixture(scope="module")
def mod():
    import odoo.service.lifecycle as m

    return m


@pytest.fixture(scope="module")
def srv():
    import odoo.service.server as m

    return m


def make_config(**overrides):
    base = {
        "db_maxconn": 64,
        "db_maxconn_gevent": None,
        "db_port": 5432,
        "workers": 0,
        "max_cron_threads": 2,
        "job_workers": 2,
        "http_enable": True,
    }
    base.update(overrides)
    return base


def limits_cursor(max_connections=100, reserved=3, server_port=5432):
    cr = MagicMock()
    cr.fetchscalar.side_effect = [str(max_connections), str(reserved), server_port]
    return cr


class TestConnectionBudgetDemand:
    def test_threaded_is_a_single_process(self, mod):
        with server_settings.override(**make_config(workers=0)):
            assert mod._get_connection_budget_demand() == (1, 64)

    def test_prefork_counts_http_cron_job_and_the_evented_child(self, mod):
        with server_settings.override(
            **make_config(workers=4, max_cron_threads=2, job_workers=2)
        ):
            processes, demand = mod._get_connection_budget_demand()
        assert processes == 9
        assert demand == 9 * 64

    def test_evented_child_uses_its_own_ceiling_when_set(self, mod):
        with server_settings.override(
            **make_config(
                workers=1, max_cron_threads=0, job_workers=0, db_maxconn_gevent=8
            )
        ):
            processes, demand = mod._get_connection_budget_demand()
        assert processes == 2
        assert demand == 64 + 8

    def test_no_evented_child_when_http_is_disabled(self, mod):
        with server_settings.override(
            **make_config(
                workers=2, max_cron_threads=0, job_workers=0, http_enable=False
            )
        ):
            processes, demand = mod._get_connection_budget_demand()
        assert processes == 2
        assert demand == 2 * 64

    def test_master_process_is_excluded(self, mod):
        with server_settings.override(
            **make_config(workers=1, max_cron_threads=0, job_workers=0)
        ):
            processes, _ = mod._get_connection_budget_demand()
        assert processes == 2


class TestWarnOnConnectionBudget:
    def _run(self, mod, overrides, cursor=None, connect_error=None):
        conn = MagicMock()
        conn.cursor.return_value = cursor if cursor is not None else limits_cursor()
        db_mock = MagicMock()
        if connect_error is not None:
            db_mock.db_connect.side_effect = connect_error
        else:
            db_mock.db_connect.return_value = conn
        logger = MagicMock()
        with (
            server_settings.override(**overrides),
            patch.object(mod, "db", db_mock),
            patch.object(mod, "_logger", logger),
        ):
            mod._warn_on_connection_budget()
        return logger

    def test_warns_when_demand_exceeds_the_server(self, mod):
        logger = self._run(
            mod, make_config(workers=4, max_cron_threads=2, job_workers=2)
        )
        logger.warning.assert_called_once()
        template, *args = logger.warning.call_args[0]
        message = template % tuple(args)
        assert "9 process" in message, message
        assert "576" in message, message
        assert "97" in message, message
        assert "to 10 or less" in message, message

    def test_silent_when_the_budget_fits(self, mod):
        logger = self._run(
            mod,
            make_config(workers=4, max_cron_threads=2, job_workers=2, db_maxconn=10),
        )
        logger.warning.assert_not_called()

    def test_silent_on_the_threaded_default(self, mod):
        logger = self._run(mod, make_config(workers=0))
        logger.warning.assert_not_called()

    def test_silent_when_postgres_cannot_be_asked(self, mod):
        logger = self._run(
            mod,
            make_config(workers=8),
            connect_error=RuntimeError("no route to host"),
        )
        logger.warning.assert_not_called()

    def test_suggested_ceiling_is_never_zero(self, mod):
        logger = self._run(
            mod, make_config(workers=200, max_cron_threads=0, job_workers=0)
        )
        assert logger.warning.call_args[0][-1] >= 1

    def test_no_advice_behind_a_pooler(self, mod):
        logger = self._run(
            mod,
            make_config(workers=4, max_cron_threads=2, job_workers=2),
            cursor=limits_cursor(server_port=5433),
        )
        logger.warning.assert_not_called()
        logger.info.assert_called_once()

    def test_a_unix_socket_does_not_read_as_a_pooler(self, mod):
        logger = self._run(
            mod,
            make_config(workers=4, max_cron_threads=2, job_workers=2),
            cursor=limits_cursor(server_port=None),
        )
        logger.warning.assert_called_once()

    def test_a_hostile_settings_source_cannot_break_the_boot(self, mod):
        logger = MagicMock()
        with (
            patch.object(mod, "current", side_effect=RuntimeError("settings gone")),
            patch.object(mod, "db", MagicMock()),
            patch.object(mod, "_logger", logger),
        ):
            mod._warn_on_connection_budget()
        logger.warning.assert_not_called()

    def test_skipped_in_the_evented_child(self, mod):
        import odoo

        db_mock = MagicMock()
        logger = MagicMock()
        with (
            patch.object(odoo, "evented", True),
            patch.object(mod, "db", db_mock),
            patch.object(mod, "_logger", logger),
        ):
            mod._warn_on_connection_budget()
        db_mock.db_connect.assert_not_called()
        logger.warning.assert_not_called()


class TestNarrowingTestSpec:
    @pytest.fixture
    def spec(self, mod):
        return mod._get_narrowing_test_spec

    def _with_tags(self, tags):
        import odoo.tools

        return odoo.tools.config.patch(test_tags=tags)

    @pytest.mark.parametrize("tags", ["", None, "+standard"])
    def test_implicit_selection_is_not_narrowing(self, spec, tags):
        with self._with_tags(tags):
            assert spec() == ""

    @pytest.mark.parametrize(
        "tags",
        [
            "/web:WebSuite.test_core[@web/core/domain]",
            "/base,-:TestReportsRendering",
            "post_install",
        ],
    )
    def test_explicit_selection_is_narrowing(self, spec, tags):
        with self._with_tags(tags):
            assert spec() == tags

    def test_surrounding_whitespace_is_ignored(self, spec):
        with self._with_tags("  +standard  "):
            assert spec() == ""


def preload_config(**overrides):
    base = {
        "limit_memory_soft": 0,
        "init": (),
        "update": (),
        "reinit": (),
        "test_enable": False,
    }
    base.update(overrides)
    return base


def make_report(*, successful=True, tests_run=1):
    report = MagicMock()
    report.wasSuccessful.return_value = successful
    report.testsRun = tests_run
    return report


class TestPreloadRegistriesReturnCode:
    @pytest.fixture
    def preload(self, mod):
        def _run(
            dbnames,
            *,
            report=None,
            config_overrides=None,
            spec="",
            new=None,
            unrun=0,
        ):
            registry = MagicMock()
            registry_cls = MagicMock()
            registry_cls.new = new or MagicMock(return_value=registry)
            registry_cls.registries.count = 1
            logger = MagicMock()
            with (
                patch.object(mod, "Registry", registry_cls),
                patch(
                    "odoo.tests.result.assertion_report",
                    MagicMock(return_value=report),
                ),
                server_settings.override(**preload_config(**(config_overrides or {}))),
                patch.object(
                    mod, "_run_post_install_tests", return_value=unrun
                ) as post_install,
                patch.object(mod, "_get_narrowing_test_spec", return_value=spec),
                patch.object(mod, "_logger", logger),
            ):
                rc = mod.preload_registries(dbnames)
            return rc, logger, registry_cls, post_install

        return _run

    def test_clean_preload_returns_zero(self, preload):
        rc, _, _, _ = preload(["db1"], report=make_report())
        assert rc == 0

    def test_no_databases_is_not_a_failure(self, preload):
        assert preload([])[0] == 0
        assert preload(None)[0] == 0

    def test_failed_assertions_raise_the_return_code(self, preload):
        rc, _, _, _ = preload(
            ["db1"],
            report=make_report(successful=False),
            config_overrides={"test_enable": True},
        )
        assert rc == 1

    def test_every_failing_database_counts(self, preload):
        rc, _, _, _ = preload(
            ["a", "b", "c"],
            report=make_report(successful=False),
            config_overrides={"test_enable": True},
        )
        assert rc == 3

    def test_a_narrowed_spec_that_ran_nothing_fails_the_run(self, preload):
        rc, logger, _, _ = preload(
            ["db1"],
            report=make_report(tests_run=0),
            config_overrides={"test_enable": True},
            spec="/web:WebSuite.test_core.@web/core/domain",
        )
        assert rc == 1
        logged = " ".join(str(c) for c in logger.error.call_args_list)
        assert "matched no test" in logged
        assert "/web:WebSuite.test_core.@web/core/domain" in logged, (
            "the operator has to see which spec matched nothing"
        )

    def test_zero_tests_without_an_explicit_spec_is_fine(self, preload):
        rc, logger, _, _ = preload(
            ["db1"],
            report=make_report(tests_run=0),
            config_overrides={"test_enable": True},
            spec="",
        )
        assert rc == 0
        logger.error.assert_not_called()

    def test_a_successful_run_is_never_second_guessed(self, preload):
        rc, _, _, _ = preload(
            ["db1"],
            report=make_report(tests_run=5),
            config_overrides={"test_enable": True},
            spec="/base",
        )
        assert rc == 0

    def test_a_post_install_phase_that_ran_nothing_fails_the_run(self, preload):
        # The hole the narrowed-spec branch above cannot see: at_install ran,
        # so the report holds tests, and every post_install class skipped
        # itself at setUpClass -- `--no-http` against HttpCase-only classes --
        # so the phase collected 25 and started none. testsRun is counted at
        # startTest, which a class-level skip never reaches.
        rc, logger, _, _ = preload(
            ["db1"],
            report=make_report(tests_run=310),
            config_overrides={"test_enable": True},
            unrun=25,
        )
        assert rc == 1
        logger.error.assert_called_once()
        message, *args = logger.error.call_args.args
        assert "post_install prepared %d tests" in message
        assert args == [25, "db1"], (
            "the operator has to see how many were prepared and for which database"
        )

    def test_a_post_install_phase_that_ran_something_is_not_hollow(self, preload):
        rc, logger, _, _ = preload(
            ["db1"],
            report=make_report(tests_run=310),
            config_overrides={"test_enable": True},
            unrun=0,
        )
        assert rc == 0
        logger.error.assert_not_called()

    def test_a_failed_run_is_counted_once_even_when_hollow(self, preload):
        rc, _, _, _ = preload(
            ["db1"],
            report=make_report(successful=False),
            config_overrides={"test_enable": True},
            unrun=25,
        )
        assert rc == 1

    def test_post_install_tests_are_skipped_without_test_enable(self, preload):
        _, _, _, post_install = preload(["db1"], report=make_report())
        post_install.assert_not_called()

    def test_a_broken_database_aborts_the_whole_preload(self, preload):
        boom = MagicMock(side_effect=RuntimeError("registry is toast"))
        rc, logger, registry_cls, _ = preload(["db1", "db2"], new=boom)
        assert rc == -1
        assert registry_cls.new.call_count == 1, "db2 should never be attempted"
        logger.critical.assert_called_once()
        assert "db1" in str(logger.critical.call_args)

    def test_a_broken_database_marks_its_test_report_aborted(self, preload):
        report = make_report(tests_run=96)
        boom = MagicMock(side_effect=RuntimeError("registry is toast"))
        rc, _, _, _ = preload(
            ["db1"],
            report=report,
            new=boom,
            config_overrides={"test_enable": True},
        )
        assert rc == -1
        report.record_abort.assert_called_once_with("RuntimeError: registry is toast")

    def test_the_registry_cache_grows_to_hold_every_database(self, preload):
        _, _, registry_cls, _ = preload(
            [f"db{i}" for i in range(40)], report=make_report()
        )
        assert registry_cls.registries.count >= 40


class TestAbortedRunReport:
    def test_an_aborted_run_is_not_summarised_as_clean(self):
        from odoo.tests.result import OdooTestResult

        report = OdooTestResult()
        report.testsRun = 96
        report.record_abort("FileNotFoundError: esbuild is required")

        assert not report.wasSuccessful()
        assert str(report).startswith("0 failed, 1 error(s) of 96 tests")
        assert "aborted before it finished: FileNotFoundError" in str(report)

    def test_merging_a_report_keeps_its_abort(self):
        from odoo.tests.result import OdooTestResult

        aborted = OdooTestResult()
        aborted.record_abort("RuntimeError: boom")
        merged = OdooTestResult()
        merged.update(aborted)

        assert not merged.wasSuccessful()
        assert merged.aborted == "RuntimeError: boom"


class TestReexecNtServiceRestart:
    def _run(self, scm_returncode):
        from odoo.service import lifecycle

        with (
            patch.object(
                lifecycle.osutil, "is_running_as_nt_service", return_value=True
            ),
            patch.object(
                lifecycle.subprocess, "call", return_value=scm_returncode
            ) as mock_call,
            patch.object(lifecycle.os, "execve") as mock_execve,
        ):
            lifecycle._reexec_server()
        return mock_call, mock_execve

    def test_successful_scm_restart_does_not_also_reexec(self):
        mock_call, mock_execve = self._run(0)
        mock_call.assert_called_once()
        mock_execve.assert_not_called()

    def test_failed_scm_restart_falls_back_to_reexec(self):
        mock_call, mock_execve = self._run(2)
        mock_call.assert_called_once()
        mock_execve.assert_called_once()


class TestServerPhoenixSingleSourceOfTruth:
    def test_process_state_is_the_canonical_holder(self):
        assert hasattr(_process_state, "server")
        assert hasattr(_process_state, "server_phoenix")

    def test_no_other_module_keeps_a_copy(self):
        """A second binding is a second answer the moment either is written."""
        from odoo.service import _factory, _threaded, _watcher, lifecycle, metrics

        for mod in (_factory, metrics, _threaded, _watcher, lifecycle):
            for name in ("server", "server_phoenix"):
                assert name not in vars(mod), (
                    f"{mod.__name__} binds {name} itself; writes through "
                    f"_process_state would not be seen there"
                )

    def test_server_module_does_not_forward_phoenix(self, srv):
        with pytest.raises(AttributeError):
            _ = srv.server_phoenix

    def test_server_module_does_not_forward_server(self, srv):
        with pytest.raises(AttributeError):
            _ = srv.server


class TestLifecycleStartWatcherCleanup:
    def test_watcher_stopped_when_server_run_raises(self):
        import odoo
        from odoo.service import _factory

        mock_server = MagicMock()
        mock_server.run.side_effect = OSError(errno.EADDRINUSE, "address in use")
        mock_watcher = MagicMock()
        fake_config = {
            **dict(odoo.tools.config.options),
            "workers": 0,
            "dev_mode": ["reload"],
            "server_wide_modules": [],
        }

        with (
            patch.object(_factory, "load_server_wide_modules"),
            server_settings.installed(
                server_settings.ServerSettings.from_config(fake_config)
            ),
            patch.object(odoo, "evented", False),
            patch.object(_factory, "ThreadedServer", return_value=mock_server),
            patch.object(_factory, "inotify", True),
            patch.object(_factory, "FSWatcherInotify", return_value=mock_watcher),
            patch.object(_process_state, "server_phoenix", False),
            patch.object(_process_state, "server", None),
            pytest.raises(OSError),
        ):
            _factory.start()

        mock_watcher.start.assert_called_once()
        mock_watcher.stop.assert_called_once()


class TestRestartGuard:
    def test_restart_with_none_server_is_noop(self, srv, caplog):
        with (
            patch("odoo.service._process_state.server", None),
            patch.object(os, "kill") as mock_kill,
            patch.object(threading, "Thread") as mock_thread,
            caplog.at_level("WARNING", logger="odoo.service.server"),
        ):
            srv.restart()

        mock_kill.assert_not_called()
        mock_thread.assert_not_called()
        assert any("restart() called before" in m for m in caplog.messages)

    def test_restart_with_real_server_posix_sends_sighup(self, srv):
        fake_server = MagicMock()
        fake_server.pid = 12345

        with (
            patch("odoo.service._process_state.server", fake_server),
            patch("odoo.service.lifecycle.IS_WINDOWS", False),
            patch.object(os, "kill") as mock_kill,
        ):
            srv.restart()

        mock_kill.assert_called_once_with(12345, signal.SIGHUP)

    def test_threaded_server_reload_delegates_to_lifecycle(self, srv):
        ts = threaded_server()
        ts.pid = 12345
        with patch("odoo.service._threaded.restart") as mock_restart:
            ts.reload()
        mock_restart.assert_called_once_with()

    def test_threaded_server_reload_is_windows_safe(self, srv):
        ts = threaded_server()
        ts.pid = 12345
        from odoo.service import lifecycle

        with (
            patch("odoo.service._process_state.server", ts),
            patch.object(lifecycle, "IS_WINDOWS", True),
            patch.object(lifecycle, "_reexec_server") as mock_reexec,
            patch.object(lifecycle.threading, "Thread") as mock_thread,
        ):
            ts.reload()
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        target = kwargs.get("target", args[0] if args else None)
        assert target is mock_reexec, (
            f"the Windows restart branch spawned a thread on {target!r}, not "
            f"_reexec_server; the process would never re-exec"
        )
        mock_thread.return_value.start.assert_called_once()


class TestSigHupSentinel:
    def test_local_sentinel_exported(self):
        from odoo.service import _base_server

        assert hasattr(_base_server, "SIGHUP_AVAILABLE")
        assert isinstance(_base_server.SIGHUP_AVAILABLE, bool)

    def test_on_posix_sentinel_is_true(self):
        import os

        from odoo.service import _base_server

        if os.name == "posix":
            assert _base_server.SIGHUP_AVAILABLE is True

    def test_the_facade_advertises_only_what_it_exports(self):
        """`server` is the public face; private module state lives at home."""
        from odoo.service import server

        for private in ("_on_stop_hooks", "SIGHUP_AVAILABLE", "FSWatcherBase"):
            assert not hasattr(server, private), (
                f"odoo.service.server re-exports {private}, which is in no "
                f"__all__ and has no consumer outside this suite"
            )
        assert set(server.__all__) <= set(vars(server))


class TestTheOpenFileBudgetIsEnsuredAtBoot:
    """`db_maxconn` × the HTTP slots × the idle-connection budget can exceed
    the default 1024 descriptors; the process finds out on accept()."""

    def test_the_threaded_demand_counts_every_descriptor_holder(self):
        from odoo.service import lifecycle

        with (
            server_settings.override(
                workers=0, db_maxconn=64, max_cron_threads=2, job_workers=1
            ),
            patch.dict(
                os.environ,
                {
                    "ODOO_MAX_HTTP_THREADS": "30",
                    "ODOO_HTTP_MAX_IDLE_CONNECTIONS": "500",
                },
            ),
        ):
            demand = lifecycle._get_descriptor_budget_demand()
        assert demand == 64 + 30 + 500 + 3 + lifecycle.DESCRIPTOR_HEADROOM

    def test_the_prefork_demand_is_the_largest_child(self):
        from odoo.service import lifecycle

        with (
            server_settings.override(workers=4, db_maxconn=64, db_maxconn_gevent=8),
            patch.dict(
                os.environ,
                {
                    "ODOO_MAX_HTTP_THREADS": "30",
                    "ODOO_HTTP_MAX_IDLE_CONNECTIONS": "500",
                },
            ),
        ):
            demand = lifecycle._get_descriptor_budget_demand()
        assert demand == max(64 + 1, 8 + 30 + 500) + lifecycle.DESCRIPTOR_HEADROOM

    def _run(self, soft, hard, demand, caplog):
        import resource

        from odoo.service import lifecycle

        calls = []
        with (
            patch.object(
                lifecycle, "_get_descriptor_budget_demand", return_value=demand
            ),
            patch.object(resource, "getrlimit", return_value=(soft, hard)),
            patch.object(resource, "setrlimit", side_effect=lambda *a: calls.append(a)),
            caplog.at_level(logging.INFO, logger="odoo.service.server"),
        ):
            lifecycle._ensure_descriptor_budget()
        return calls, [r.getMessage() for r in caplog.records]

    def test_enough_soft_limit_touches_nothing(self, caplog):
        calls, said = self._run(4096, 4096, 800, caplog)
        assert calls == [] and said == []

    def test_a_low_soft_limit_is_raised_to_the_hard_one(self, caplog):
        import resource

        calls, said = self._run(1024, 524288, 4000, caplog)
        assert calls == [(resource.RLIMIT_NOFILE, (524288, 524288))]
        assert any("raised from 1024 to 524288" in m for m in said)

    def test_a_hard_limit_below_the_demand_is_named_with_the_remedy(self, caplog):
        calls, said = self._run(1024, 1024, 4000, caplog)
        assert calls == []
        assert any("LimitNOFILE" in m and "4000" in m for m in said)
