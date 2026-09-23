from types import SimpleNamespace
from typing import Any

from odoo.tools.assets import esm_index


def _asset(path: str, raw: str):
    return SimpleNamespace(module_path=path, url=None, raw_content=raw)


def _key(**overrides):
    params: dict[str, Any] = {
        "group": "runtime:web.assets_web:tests",
        "entries": {"a.child": [_asset("@a/x", "export const x = 1;")]},
        "templates": {"a.child": "<t/>"},
        "parent_specs": frozenset({"@web/core/registry"}),
        "secondary_stubs": {"@web/core/registry": "stub"},
        "target": "es2022",
        "source_maps": "",
    }
    params.update(overrides)
    return esm_index.group_source_key(**params)


class TestGroupSourceKey:
    def test_the_same_inputs_give_the_same_key(self):
        assert _key() == _key()

    def test_every_input_is_part_of_the_key(self):
        base = _key()
        assert (
            _key(entries={"a.child": [_asset("@a/x", "export const x = 2;")]}) != base
        )
        assert _key(templates={"a.child": "<t t-name='x'/>"}) != base
        assert _key(parent_specs=frozenset()) != base
        assert _key(secondary_stubs={}) != base
        assert _key(target="es2020") != base
        assert _key(group="runtime:web.assets_web") != base


class TestVariantKey:
    def test_no_parameter_is_the_default_variant(self):
        assert esm_index.variant_key() == esm_index.DEFAULT_VARIANT
        assert esm_index.variant_key({"website_id": None}) == esm_index.DEFAULT_VARIANT

    def test_every_selector_makes_its_own_variant(self):
        keys = {
            esm_index.variant_key(),
            esm_index.variant_key({"website_id": 1}),
            esm_index.variant_key({"website_id": 2}),
            esm_index.variant_key(page_scope=("web.assets_frontend",)),
            esm_index.variant_key(standalone=True),
        }
        assert len(keys) == 5

    def test_the_key_is_canonical(self):
        assert esm_index.variant_key(
            {"b": 2, "a": 1}, page_scope=("y", "x")
        ) == esm_index.variant_key({"a": 1, "b": 2}, page_scope=("x", "y"))
