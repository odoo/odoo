import ctypes as real_ctypes
import sys
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import lifecycle
from odoo.service import settings as server_settings


@pytest.fixture
def load_modules():
    def _run(names, failing=()):
        loaded = []

        def loader(name):
            loaded.append(name)
            if name in failing:
                raise ImportError(f"no module named {name}")

        with (
            server_settings.override(server_wide_modules=names),
            patch.object(lifecycle, "load_odoo_module", side_effect=loader),
        ):
            lifecycle.load_server_wide_modules()
        return loaded

    return _run


class TestLoadServerWideModules:
    def test_every_configured_module_is_loaded(self, load_modules):
        assert load_modules(["base", "web"]) == ["base", "web"]

    def test_one_failure_does_not_stop_the_rest(self, load_modules, caplog):
        loaded = load_modules(["base", "broken", "web"], failing={"broken"})
        assert loaded == ["base", "broken", "web"], (
            "a server-wide module that cannot import must not take the ones "
            "after it with it — the server is still worth starting"
        )

    def test_the_failure_is_logged_with_a_traceback(self, load_modules, caplog):
        load_modules(["broken"], failing={"broken"})
        assert "Failed to load server-wide module `broken`" in caplog.text
        assert any(r.exc_info for r in caplog.records), (
            "swallowing the traceback leaves a module that silently is not there"
        )

    def test_web_failing_gets_the_addons_path_hint(self, load_modules, caplog):
        load_modules(["web"], failing={"web"})
        assert "odoo-web" in caplog.text and "addons_path" in caplog.text, (
            "`web` missing is almost always a misconfigured addons_path, and "
            "the bare ImportError does not say so"
        )

    def test_an_ordinary_module_does_not_get_that_hint(self, load_modules, caplog):
        load_modules(["something_else"], failing={"something_else"})
        assert "odoo-web" not in caplog.text

    def test_the_whole_load_runs_with_gc_disabled(self, load_modules):
        with patch.object(lifecycle.gc, "disabling_gc") as disabling:
            load_modules(["base"])
        disabling.assert_called_once()


@pytest.fixture
def arenas(monkeypatch):
    def _run(*, linux=True, bits64=True, env_set=False, gil=True, mallopt=1, libc=...):
        monkeypatch.delenv("MALLOC_ARENA_MAX", raising=False)
        if env_set:
            monkeypatch.setenv("MALLOC_ARENA_MAX", "4")
        if libc is ...:
            libc = MagicMock()
            libc.mallopt.return_value = mallopt
        ctypes = MagicMock(c_int=real_ctypes.c_int)
        ctypes.CDLL.return_value = libc
        with (
            patch.object(
                lifecycle.platform,
                "system",
                return_value="Linux" if linux else "Darwin",
            ),
            patch.object(lifecycle.sys, "maxsize", 2**63 - 1 if bits64 else 2**31 - 1),
            patch.dict(sys.modules, {"ctypes": ctypes}),
        ):
            if gil:
                monkeypatch.delattr(sys, "_is_gil_enabled", raising=False)
            else:
                monkeypatch.setattr(
                    sys, "_is_gil_enabled", lambda: False, raising=False
                )
            lifecycle._limit_malloc_arenas()
        return libc

    return _run


class TestLimitMallocArenas:
    def test_on_64_bit_linux_it_caps_the_arenas(self, arenas):
        libc = arenas()
        libc.mallopt.assert_called_once()
        assert libc.mallopt.call_args.args[1].value == 2

    def test_it_uses_the_glibc_m_arena_max_option(self, arenas):
        libc = arenas()
        assert libc.mallopt.call_args.args[0].value == -8, (
            "M_ARENA_MAX is -8; any other option number silently tunes "
            "something else in glibc"
        )

    @pytest.mark.parametrize(
        ("shape", "why"),
        [
            ({"linux": False}, "glibc arenas are a glibc concept"),
            ({"bits64": False}, "32-bit does not have the arena problem"),
            ({"env_set": True}, "the operator already chose a value"),
            ({"gil": False}, "free-threading wants the arenas it asks for"),
        ],
    )
    def test_it_stays_out_of_the_way(self, arenas, shape, why):
        libc = arenas(**shape)
        assert not libc.mallopt.called, why

    def test_a_refused_mallopt_warns_and_does_not_raise(self, arenas, caplog):
        arenas(mallopt=0)
        assert "ARENA_MAX" in caplog.text

    def test_a_libc_that_will_not_load_is_not_fatal(self, arenas, caplog):
        libc = MagicMock()
        libc.mallopt.side_effect = OSError("cannot open shared object file")
        arenas(libc=libc)
        assert "ARENA_MAX" in caplog.text


def _demand(**overrides):
    cfg = {
        "db_maxconn": 64,
        "db_maxconn_gevent": 0,
        "workers": 0,
        "max_cron_threads": 0,
        "job_workers": 0,
        "stream_workers": 0,
        "http_enable": True,
        **overrides,
    }
    with server_settings.override(**cfg):
        return lifecycle._get_connection_budget_demand()


class TestConnectionBudgetDemand:
    def test_threaded_mode_is_one_process_and_its_own_pool(self):
        assert _demand(workers=0, db_maxconn=64) == (1, 64), (
            "with workers=0 there is no fork, so the whole demand is this "
            "process's pool"
        )

    def test_prefork_multiplies_the_pool_by_every_child(self):
        processes, demand = _demand(
            workers=4, max_cron_threads=2, job_workers=1, db_maxconn=64
        )
        assert (processes, demand) == (7 + 1, 7 * 64 + 64), (
            "db_maxconn is PER PROCESS. Four http workers, two cron and one "
            "job at the default 64 already demand 512 connections before the "
            "gevent process, against a cluster that ships with 100"
        )

    def test_the_gevent_process_is_counted(self):
        with_http = _demand(workers=2, http_enable=True)
        without = _demand(workers=2, http_enable=False)
        assert with_http[0] == without[0] + 1
        assert with_http[1] == without[1] + 64, (
            "the longpolling process holds its own pool; leaving it out "
            "under-reports the demand by a whole db_maxconn"
        )

    def test_a_separate_gevent_pool_size_is_honoured(self):
        _, demand = _demand(workers=2, db_maxconn=64, db_maxconn_gevent=8)
        assert demand == 2 * 64 + 8, (
            "db_maxconn_gevent exists because the longpolling process needs far "
            "fewer connections than an http worker"
        )

    def test_zero_gevent_pool_falls_back_to_db_maxconn(self):
        _, demand = _demand(workers=1, db_maxconn=64, db_maxconn_gevent=0)
        assert demand == 2 * 64, "0 means unset, not a pool of zero"

    def test_cron_job_and_stream_workers_count_as_processes(self):
        assert (
            _demand(workers=1, max_cron_threads=3, job_workers=2, stream_workers=1)[0]
            == 7 + 1
        ), (
            "they are forked children with their own pools, not threads inside "
            "an http worker"
        )
