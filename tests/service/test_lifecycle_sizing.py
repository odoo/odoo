from unittest.mock import patch

import pytest

from odoo.modules.registry import Registry
from odoo.service import lifecycle
from odoo.service import settings as server_settings

AVG_REGISTRY_BYTES = 15 * 1024 * 1024

DEFAULT_SOFT_LIMIT = 2048 * 1024 * 1024


@pytest.fixture
def registry_limits():
    count, idle = Registry.registries.count, Registry.idle_timeout
    yield
    Registry.registries.count, Registry.idle_timeout = count, idle


@pytest.fixture
def sizing(monkeypatch, registry_limits):
    monkeypatch.delenv("ODOO_REGISTRY_LRU_SIZE", raising=False)
    monkeypatch.delenv("ODOO_REGISTRY_MAX_IDLE_TIMEOUT", raising=False)

    def _run(dbnames=(), *, env=None, config=None, posix=True, resident=1):
        for key, value in (env or {}).items():
            monkeypatch.setenv(key, value)
        cfg = {"limit_memory_soft": 0, **(config or {})}
        Registry.registries.count = resident
        with (
            server_settings.override(**cfg),
            patch.object(lifecycle, "IS_POSIX", posix),
        ):
            lifecycle._limit_resident_registries(list(dbnames))
        return Registry.registries.count, Registry.idle_timeout

    return _run


class TestResidentCount:
    def test_an_explicit_lru_size_wins_outright(self, sizing):
        count, _ = sizing(
            ["a", "b", "c"],
            env={"ODOO_REGISTRY_LRU_SIZE": "7"},
            config={"limit_memory_soft": 900 * 1024 * 1024},
        )
        assert count == 7, (
            "ODOO_REGISTRY_LRU_SIZE is the operator saying what they want; "
            "neither the memory estimate nor the database count may override it"
        )

    def test_the_default_budget_is_derived_from_the_soft_memory_limit(self, sizing):
        count, _ = sizing(config={"limit_memory_soft": 900 * 1024 * 1024})
        assert count == (900 * 1024 * 1024) // AVG_REGISTRY_BYTES == 60

    def test_no_soft_limit_falls_back_to_a_bounded_default_not_infinity(self, sizing):
        count, _ = sizing(config={"limit_memory_soft": 0})
        assert count == DEFAULT_SOFT_LIMIT // AVG_REGISTRY_BYTES == 136, (
            "with no configured soft limit the budget must still be a number; "
            "an unbounded resident set is how a worker OOMs instead of recycling"
        )

    def test_a_soft_limit_below_one_registry_still_allows_one(self, sizing):
        count, _ = sizing(
            config={"limit_memory_soft": AVG_REGISTRY_BYTES // 2}, resident=42
        )
        assert count == 1, (
            "the `or 1` floor: a budget that divides to zero would make the LRU "
            "evict every registry the moment it was created"
        )

    def test_more_databases_than_the_budget_widens_it_to_hold_them(self, sizing):
        dbnames = [f"db{i}" for i in range(200)]
        count, _ = sizing(dbnames, config={"limit_memory_soft": 900 * 1024 * 1024})
        assert count == 200, (
            "preloading 200 databases into a 60-slot LRU evicts the first 140 "
            "as it loads the rest, so the preload does no work"
        )

    def test_the_widening_compares_against_what_is_already_resident(self, sizing):
        count, _ = sizing(
            [f"db{i}" for i in range(100)],
            config={"limit_memory_soft": 900 * 1024 * 1024},
            resident=500,
        )
        assert count == 60, (
            f"the LRU already holds 500 registries, so 100 databases fit "
            f"without widening anything — but the budget was raised to {count}. "
            f"The comparison must be against max(budget, resident), not the "
            f"budget alone."
        )

    def test_a_short_database_list_does_not_shrink_the_budget(self, sizing):
        count, _ = sizing(
            ["a", "b"], config={"limit_memory_soft": 900 * 1024 * 1024}, resident=500
        )
        assert count == 60

    def test_off_posix_the_budget_comes_only_from_the_database_list(self, sizing):
        count, _ = sizing(
            ["a", "b", "c"],
            config={"limit_memory_soft": 900 * 1024 * 1024},
            posix=False,
            resident=1,
        )
        assert count == 3, (
            "the memory estimate reads a POSIX-only soft limit, so off POSIX "
            "the only floor left is the number of databases being preloaded"
        )

    def test_off_posix_with_nothing_to_preload_leaves_the_lru_alone(self, sizing):
        count, _ = sizing([], posix=False, resident=42)
        assert count == 42, "a zero budget must not be written over the live one"


class TestIdleTimeout:
    def test_it_is_off_unless_asked_for(self, sizing):
        _, idle = sizing()
        assert idle == Registry.idle_timeout
        assert not idle, "dropping idle registries must be opt-in"

    def test_the_environment_sets_it(self, sizing):
        _, idle = sizing(env={"ODOO_REGISTRY_MAX_IDLE_TIMEOUT": "900"})
        assert idle == 900

    def test_the_config_key_sets_it_when_the_environment_does_not(self, sizing):
        _, idle = sizing(config={"registry_idle_timeout": 300})
        assert idle == 300

    def test_the_environment_wins_over_the_config_key(self, sizing):
        _, idle = sizing(
            env={"ODOO_REGISTRY_MAX_IDLE_TIMEOUT": "60"},
            config={"registry_idle_timeout": 300},
        )
        assert idle == 60

    def test_a_negative_environment_value_is_refused_not_applied(self, sizing):
        _, idle = sizing(env={"ODOO_REGISTRY_MAX_IDLE_TIMEOUT": "-5"})
        assert not idle, (
            "get_env_int has minimum=0, so a negative timeout falls back to the "
            "default rather than arming an always-expired registry"
        )

    def test_a_negative_environment_value_still_lets_the_config_key_through(
        self, sizing
    ):
        _, idle = sizing(
            env={"ODOO_REGISTRY_MAX_IDLE_TIMEOUT": "-5"},
            config={"registry_idle_timeout": 300},
        )
        assert idle == 300, (
            "a rejected environment value must clamp to 0 so the configured "
            "timeout is still applied; instead the negative value was kept, "
            "was truthy, and shadowed the config key"
        )

    def test_a_garbage_environment_value_does_not_crash_the_boot(self, sizing):
        count, idle = sizing(env={"ODOO_REGISTRY_LRU_SIZE": "not-a-number"})
        assert not idle
        assert count == DEFAULT_SOFT_LIMIT // AVG_REGISTRY_BYTES, (
            "an unparseable LRU size must fall through to the derived budget, "
            "not abort the server before it serves anything"
        )
