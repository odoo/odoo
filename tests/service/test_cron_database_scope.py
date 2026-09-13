import pytest

from odoo.service import _cron, _dispatch, _limits
from odoo.service import settings as server_settings


@pytest.fixture
def scoped():
    _dispatch._compile_static_dbfilter.cache_clear()

    def _scoped(**overrides):
        return server_settings.override(**{"db_name": (), "dbfilter": "", **overrides})

    return _scoped


@pytest.fixture
def catalogue(monkeypatch):
    names = ["alpha_prod", "alpha_test", "beta_prod", "postgres", "tpl"]
    monkeypatch.setattr(_cron, "list_dbs", lambda force: list(names))
    monkeypatch.setattr(
        _cron, "is_maintenance_db", lambda n: n in {"postgres", "template1", "tpl"}
    )
    return names


class TestCronDatabaseList:
    def test_db_name_wins_and_is_copied(self, scoped, catalogue):
        with scoped(db_name=("only_this",)) as settings:
            got = _cron.get_cron_databases()
        assert got == ["only_this"]
        got.append("mutated")
        assert settings.db_name == ("only_this",), "the caller mutated the snapshot"

    def test_maintenance_databases_never_get_cron(self, scoped, catalogue):
        with scoped():
            assert _cron.get_cron_databases() == [
                "alpha_prod",
                "alpha_test",
                "beta_prod",
            ]

    def test_a_static_dbfilter_scopes_the_sweep(self, scoped, catalogue):
        with scoped(dbfilter="alpha_.*"):
            assert _cron.get_cron_databases() == ["alpha_prod", "alpha_test"]

    def test_a_host_dependent_dbfilter_cannot_scope_and_says_so(
        self, scoped, catalogue, caplog
    ):
        with (
            scoped(dbfilter="%d_prod"),
            caplog.at_level("WARNING", logger="odoo.service.server"),
        ):
            assert _cron.get_cron_databases() == [
                "alpha_prod",
                "alpha_test",
                "beta_prod",
            ]
        assert "cannot scope cron" in caplog.text

    def test_the_host_dependent_warning_fires_once_per_process(
        self, scoped, catalogue, caplog
    ):
        with (
            scoped(dbfilter="%h"),
            caplog.at_level("WARNING", logger="odoo.service.server"),
        ):
            for _ in range(5):
                _cron.get_cron_databases()
        assert caplog.text.count("cannot scope cron") == 1

    def test_an_invalid_dbfilter_does_not_take_the_sweep_down(
        self, scoped, catalogue, caplog
    ):
        with (
            scoped(dbfilter="alpha_[("),
            caplog.at_level("WARNING", logger="odoo.service.server"),
        ):
            assert _cron.get_cron_databases() == [
                "alpha_prod",
                "alpha_test",
                "beta_prod",
            ]
        assert "not a valid regular expression" in caplog.text

    def test_the_filter_anchors_at_the_start_like_db_filter_does(
        self, scoped, catalogue
    ):
        with scoped(dbfilter="prod"):
            assert _cron.get_cron_databases() == []


class TestInheritFromCron:
    def test_the_sentinel_is_the_one_the_budgets_compare_against(self):
        with server_settings.override(
            limit_time_worker_job=_limits.INHERIT_FROM_CRON,
            limit_time_worker_cron=900,
            limit_time_real_job=_limits.INHERIT_FROM_CRON,
            limit_time_real_cron=300,
            limit_time_real=120,
        ):
            assert server_settings.current().job_max_age == 900
            assert _limits.get_job_real_time_budget() == 300

    def test_zero_disables_rather_than_inherits(self):
        with server_settings.override(
            limit_time_worker_job=0, limit_time_worker_cron=900
        ):
            assert server_settings.current().job_max_age == 0
