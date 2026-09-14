import json
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


class TestGroupIndex:
    def test_the_pointer_url_is_a_path(self):
        url = esm_index.group_index_url("runtime:web.assets_web+x:tests", "abc")
        assert ":" not in url.rsplit("/", 1)[-1] and "+" not in url
        assert url.startswith("/web/assets/esm/by-source/abc/")

    def test_a_pointer_resolves_only_when_every_child_is_readable(self):
        row = esm_index.group_index_row(
            "g",
            "k",
            {"a": "/web/assets/esm/h/a.esm.js", "b": "/web/assets/esm/h/b.esm.js"},
        )
        assert row["url"] == esm_index.group_index_url("g", "k")
        store = {row["url"]: row["raw"], "/web/assets/esm/h/a.esm.js": b"a"}
        assert esm_index.resolve_group_index(store.get, "g", "k") is None
        store["/web/assets/esm/h/b.esm.js"] = b"b"
        assert (
            esm_index.resolve_group_index(store.get, "g", "k")
            == json.loads(row["raw"])["urls"]
        )

    def test_a_missing_or_malformed_pointer_is_a_miss(self):
        assert esm_index.resolve_group_index(lambda url: None, "g", "k") is None
        assert (
            esm_index.resolve_group_index(lambda url: b'{"urls": []}', "g", "k") is None
        )
        assert esm_index.resolve_group_index(lambda url: b"nope", "g", "k") is None
