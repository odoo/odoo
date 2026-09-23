from unittest.mock import patch

from odoo.orm.runtime import registry as reg_mod
from odoo.orm.runtime.registry import Registry

DB = "test_registry_gc_freeze_db"


def test_removing_a_registry_thaws_the_heap():
    Registry.registries[DB] = object.__new__(Registry)
    with patch.object(reg_mod.gc, "thaw") as thaw:
        Registry.remove(DB)
    (
        thaw.assert_called_once_with(),
        ("a registry frozen at load and removed without a rebuild is never collected"),
    )


def test_removing_an_absent_registry_leaves_the_heap_frozen():
    with patch.object(reg_mod.gc, "thaw") as thaw:
        Registry.remove(DB)
    thaw.assert_not_called()


class _FakeRegistries(dict):
    count = 0


def test_removing_every_registry_thaws_the_heap():
    with (
        patch.object(Registry, "registries", _FakeRegistries(db=object())),
        patch.object(reg_mod.gc, "thaw") as thaw,
        patch.object(reg_mod, "clear_all_text_transforms"),
        patch("odoo.tests.result.forget_assertion_report"),
    ):
        Registry.remove_all()
        assert not Registry.registries
    thaw.assert_called_once_with()


def test_a_ready_registry_freezes_what_survives():
    registry = object.__new__(Registry)
    Registry.registries[DB] = registry
    try:
        with (
            patch.object(reg_mod.gc, "freeze_survivors") as freeze,
            patch.object(Registry, "_get_field_triggers"),
            patch.object(Registry, "signal_changes"),
            patch.object(Registry, "_evict_idle_registries"),
        ):
            registry._init_signaling_state()
            registry.models = {}
            registry.loaded_modules = set()
            registry.updated_modules = []
            Registry._new_finalize(DB, False, 0.0)
        freeze.assert_called_once_with()
    finally:
        Registry.registries.pop(DB, None)


def test_a_registry_evicted_for_capacity_thaws_the_heap():
    saved = Registry.registries.snapshot
    count = Registry.registries.count
    try:
        Registry.registries.clear()
        Registry.registries.count = 1
        Registry.registries[DB] = object.__new__(Registry)
        with (
            patch.object(reg_mod.gc, "thaw") as thaw,
            patch.object(reg_mod, "remove_counters") as counters,
        ):
            Registry.registries[DB + "_next"] = object.__new__(Registry)
        assert DB not in Registry.registries
        (
            thaw.assert_called_once_with(),
            ("a registry the LRU pushes out is otherwise frozen for good"),
        )
        counters.assert_called_once_with(DB)
    finally:
        Registry.registries.clear()
        Registry.registries.count = count
        for db_name, registry in saved.items():
            Registry.registries[db_name] = registry
