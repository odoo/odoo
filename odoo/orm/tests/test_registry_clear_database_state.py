import pytest

from odoo.orm.runtime import _registry_capabilities as cap_mod
from odoo.orm.runtime import registry as reg_mod
from odoo.orm.runtime.registry import Registry
from odoo.tests import result as result_module

DB = "test_registry_clear_database_state_db"


@pytest.fixture
def seeded():
    cap_mod._TextTables.by_db[DB] = cap_mod._TextTransforms(
        True, {0xE9: "e"}, {0xC9: "e"}
    )
    result_module._ASSERTION_REPORTS[DB] = result_module.OdooTestResult()
    try:
        yield
    finally:
        cap_mod._TextTables.by_db.pop(DB, None)
        result_module._ASSERTION_REPORTS.pop(DB, None)
        Registry.registries.pop(DB, None)


def test_delete_keeps_what_must_survive_a_rebuild(seeded):
    Registry.remove(DB)

    assert DB in result_module._ASSERTION_REPORTS, (
        "Registry.remove dropped the assertion report. It runs inside "
        "Registry.new on every rebuild, so this makes a registry reload discard "
        "every failure recorded before it and exit 0 -- the defect "
        "_ASSERTION_REPORTS was introduced to fix."
    )
    assert DB in cap_mod._TextTables.by_db, (
        "Registry.remove dropped the database text transforms. Rebuilding them "
        "probes PostgreSQL again on every registry rebuild."
    )


def test_clear_database_state_drops_every_per_database_map(seeded):
    Registry.clear_database_state(DB)

    assert DB not in cap_mod._TextTables.by_db
    assert DB not in result_module._ASSERTION_REPORTS
    assert DB not in Registry.registries


def test_clear_database_state_is_idempotent(seeded):
    Registry.clear_database_state(DB)
    Registry.clear_database_state(DB)


def test_delete_all_clears_the_per_database_maps(seeded):
    Registry.remove_all()

    assert not cap_mod._TextTables.by_db
    assert not result_module._ASSERTION_REPORTS
    assert not Registry.registries


def test_teardown_call_sites_use_clear_database_state_not_delete():
    import pathlib

    root = pathlib.Path(reg_mod.__file__).resolve().parents[3]
    expected = {
        "odoo/service/db/lifecycle.py": 2,
        "odoo/http/_serve.py": 1,
    }
    for rel, count in expected.items():
        text = (root / rel).read_text()
        assert text.count("Registry.clear_database_state(") == count, (
            f"{rel} should call Registry.clear_database_state {count}x"
        )
        assert "Registry.remove(" not in text, (
            f"{rel} calls Registry.remove; a database that is gone must be "
            f"forgotten, or its unaccent table and assertion report leak for "
            f"the life of the process"
        )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
