import inspect

from odoo.orm.runtime.savepoint import _OrmFlushingSavepoint


class _FakeRegistry:
    def __init__(self, generation=None):
        self.cache_invalidation_generation = dict(generation or {})
        self.cache_invalidated = set(self.cache_invalidation_generation)
        self.cleared = []

    def clear_cache(self, *names):
        self.cleared.append(names)
        self.cache_invalidated.update(names)
        for name in names:
            self.cache_invalidation_generation[name] = (
                self.cache_invalidation_generation.get(name, 0) + 1
            )


def test_every_group_invalidated_in_the_span_is_cleared_again():
    registry = _FakeRegistry({"stable": 1, "default": 1})

    _OrmFlushingSavepoint._clear_invalidated_caches(registry, {})

    assert len(registry.cleared) == 1, "expected exactly one clear_cache call"
    assert set(registry.cleared[0]) == {"stable", "default"}


def test_a_transaction_that_invalidated_nothing_pays_nothing():
    registry = _FakeRegistry()

    _OrmFlushingSavepoint._clear_invalidated_caches(registry, {})

    assert registry.cleared == [], (
        "a savepoint rollback in a transaction that wrote no cached model must not "
        "drop caches; every nested savepoint would pay for it"
    )


def test_groups_invalidated_only_before_the_span_are_left_alone():
    registry = _FakeRegistry({"stable": 3, "default": 1, "xmlid": 2})

    _OrmFlushingSavepoint._clear_invalidated_caches(
        registry, {"stable": 3, "default": 1, "xmlid": 2}
    )

    assert registry.cleared == [], (
        "a group invalidated before the savepoint opened was cleared then; what "
        "was rebuilt since saw no rolled-back write, and re-clearing it on every "
        "later rollback leaves the whole transaction cold"
    )


def test_a_group_invalidated_again_inside_the_span_is_cleared():
    registry = _FakeRegistry({"stable": 4, "default": 1})

    _OrmFlushingSavepoint._clear_invalidated_caches(
        registry, {"stable": 3, "default": 1}
    )

    assert len(registry.cleared) == 1
    assert set(registry.cleared[0]) == {"stable"}, (
        "membership is not enough: a group already invalidated before the span "
        "and written again inside it holds entries built on the rolled-back write"
    )


def test_the_groups_stay_named_so_the_commit_still_signals_peers():
    registry = _FakeRegistry({"stable": 1})

    _OrmFlushingSavepoint._clear_invalidated_caches(registry, {})

    assert registry.cache_invalidated == {"stable"}


def test_restore_orm_state_calls_it():
    src = inspect.getsource(_OrmFlushingSavepoint._restore_orm_state)
    assert "_clear_invalidated_caches" in src


def test_it_runs_before_the_registry_swap_branch():
    src = inspect.getsource(_OrmFlushingSavepoint._restore_orm_state)
    assert src.index("_clear_invalidated_caches") < src.index("txn.reset()")
