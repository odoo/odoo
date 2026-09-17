from unittest.mock import Mock, patch

import pytest

from odoo.db import FunctionStatus
from odoo.orm.runtime import _registry_capabilities as capabilities
from odoo.orm.runtime.environment import Environment

DB = "test_registry_text_transforms"


class Capabilities(capabilities._RegistryCapabilitiesMixin):
    pass


@pytest.fixture(autouse=True)
def clear_tables():
    capabilities.clear_text_transforms(DB)
    yield
    capabilities.clear_text_transforms(DB)


def test_cached_tables_are_rebuilt_when_unaccent_availability_changes():
    cursor = Mock(spec=["execute", "fetchone", "dictfetchall"])
    cursor.fetchone.return_value = ("c",)
    cursor.dictfetchall.return_value = [
        {"source": "Æ", "unaccented": "AE", "folded": "ae"},
        {"source": "\ua7ce", "unaccented": "\ua7ce", "folded": "\ua7cf"},
    ]
    first = capabilities._get_text_transforms(cursor, DB, True)
    calls = cursor.execute.call_count
    assert capabilities._get_text_transforms(cursor, DB, True) is first
    assert cursor.execute.call_count == calls
    assert first.unaccent[ord("Æ")] == "AE"
    assert first.ilike is not None
    assert first.ilike[0xA7CE] == "\ua7cf"

    cursor.dictfetchall.return_value = [
        {"source": "Æ", "unaccented": "Æ", "folded": "æ"},
    ]
    second = capabilities._get_text_transforms(cursor, DB, False)
    assert second is not first
    assert second.unaccent == {}
    assert second.ilike is not None
    assert second.ilike[ord("Æ")] == "æ"


def test_libc_normalization_uses_the_database_mapping_without_queries():
    instance = Capabilities()
    instance._text_transforms = capabilities._TextTransforms(
        True, {}, {0xA7CE: "\ua7cf", ord("Æ"): "ae"}
    )
    env = Mock(spec=Environment)
    normalize = instance.get_ilike_normalizer(env)
    assert normalize("\ua7ceÆ") == "\ua7cfae"
    env.execute_query.assert_not_called()


def test_contextual_normalization_caches_whole_strings_per_environment():
    instance = Capabilities()
    instance._text_transforms = capabilities._TextTransforms(False, {}, None)
    instance.unaccent = capabilities._identity
    first_env = Mock(spec=Environment)
    first_env.execute_query.return_value = [("ος",)]
    normalize = instance.get_ilike_normalizer(first_env)
    assert normalize("ΟΣ") == "ος"
    assert normalize("ΟΣ") == "ος"
    first_env.execute_query.assert_called_once()

    second_env = Mock(spec=Environment)
    second_env.execute_query.return_value = [("other",)]
    assert instance.get_ilike_normalizer(second_env)("ΟΣ") == "other"
    second_env.execute_query.assert_called_once()


def test_contextual_providers_do_not_expose_a_character_case_table():
    cursor = Mock(spec=["execute", "fetchone", "dictfetchall"])
    cursor.fetchone.return_value = ("i",)
    cursor.dictfetchall.return_value = []
    assert capabilities._get_text_transforms(cursor, DB, False).ilike is None


def test_failed_probes_do_not_publish_partial_tables():
    cursor = Mock(spec=["execute", "fetchone", "dictfetchall"])
    cursor.fetchone.return_value = ("c",)
    cursor.dictfetchall.side_effect = RuntimeError("probe failed")
    with pytest.raises(RuntimeError, match="probe failed"):
        capabilities._get_text_transforms(cursor, DB, True)
    assert DB not in capabilities._TextTables.by_db


def test_probe_does_not_build_the_tables_until_a_normalizer_is_asked_for():
    instance = Capabilities()
    instance.db_name = DB
    probe = Mock(spec=["execute", "fetchone", "fetchall", "dictfetchall"])
    probe.fetchone.return_value = (None,)
    with (
        patch.object(
            capabilities,
            "get_unaccent_status",
            return_value=FunctionStatus.INDEXABLE,
        ),
        patch.object(capabilities, "has_trigram", return_value=True),
    ):
        instance._probe_capabilities(probe, DB)
    assert instance._text_transforms is None
    probe.execute.assert_not_called()

    cursor = Mock(spec=["execute", "fetchone", "dictfetchall"])
    cursor.fetchone.return_value = ("c",)
    cursor.dictfetchall.return_value = [
        {"source": "Æ", "unaccented": "AE", "folded": "ae"},
    ]
    env = Mock(spec=Environment)
    env.cr = cursor
    assert instance.get_ilike_normalizer(env)("Æ") == "ae"
    assert instance.unaccent_python("Æ") == "AE"
    assert cursor.execute.call_count == 2
    assert instance._text_transforms is capabilities._TextTables.by_db[DB]


def test_probe_adopts_tables_this_process_already_built_for_the_database():
    built = capabilities._TextTransforms(True, {ord("Æ"): "AE"}, None)
    capabilities._TextTables.by_db[DB] = built
    instance = Capabilities()
    instance.db_name = DB
    probe = Mock(spec=["execute", "fetchone", "fetchall", "dictfetchall"])
    with (
        patch.object(
            capabilities,
            "get_unaccent_status",
            return_value=FunctionStatus.INDEXABLE,
        ),
        patch.object(capabilities, "has_trigram", return_value=False),
    ):
        instance._probe_capabilities(probe, DB)
    assert instance._text_transforms is built
    assert instance.unaccent_python("Æ") == "AE"
    probe.execute.assert_not_called()


def test_concurrent_cold_callers_build_the_tables_once():
    import threading

    cursor = Mock(spec=["execute", "fetchone", "dictfetchall"])
    cursor.fetchone.return_value = ("c",)
    cursor.dictfetchall.return_value = []
    gate = threading.Barrier(8)
    results = []

    def build():
        gate.wait()
        results.append(capabilities._get_text_transforms(cursor, DB, True))

    threads = [threading.Thread(target=build) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(results) == 8
    assert all(result is results[0] for result in results)
    assert cursor.execute.call_count == 2


def test_model_registry_folds_with_an_injected_normalizer():
    from odoo.orm.model_test_env import ModelRegistry

    registry = ModelRegistry([])
    assert registry.get_ilike_normalizer(None)("ΟΣ") == "οσ"
    registry.ilike_normalizer = lambda value: value.replace("A", "a")
    normalize = registry.get_ilike_normalizer(None)
    assert normalize("ΟΣ A") == "ΟΣ a"
