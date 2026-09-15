from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)
SCHEMA_PATH = Path(__file__).with_name("schema.json")
AttrType = str | list[str]


@dataclass(frozen=True, slots=True)
class NodeSpec:
    kind: str
    attrs: dict[str, AttrType]
    children: frozenset[str] | None


@dataclass(frozen=True, slots=True)
class ViewTypeSpec:
    name: str
    root: str
    nodes: dict[str, NodeSpec]


class Schema:
    def __init__(self, data: dict) -> None:
        self.version: int = data["version"]
        self.attr_types: dict[str, str] = data["attr_types"]
        self.common_attrs: dict[str, AttrType] = data["common_attrs"]
        self.html_tags: frozenset[str] = frozenset(data["html"]["tags"])
        self.html_attrs: dict[str, AttrType] = data["html"]["attrs"]
        self.patch_nodes: dict[str, NodeSpec] = {
            kind: NodeSpec(kind, spec["attrs"], None)
            for kind, spec in data["patch"]["nodes"].items()
        }
        self.patch_attrs: dict[str, AttrType] = data["patch"]["attrs"]
        self.types: dict[str, ViewTypeSpec] = {
            name: ViewTypeSpec(
                name,
                spec["root"],
                {
                    kind: NodeSpec(
                        kind,
                        node["attrs"],
                        frozenset(node["children"]) if "children" in node else None,
                    )
                    for kind, node in spec["nodes"].items()
                },
            )
            for name, spec in data["types"].items()
        }
        self.roots: dict[str, str] = {
            spec.root: name for name, spec in self.types.items()
        }

    def view_type_of(self, root_kind: str) -> str | None:
        return self.roots.get(root_kind)

    def is_html(self, kind: str) -> bool:
        return kind in self.html_tags or kind.startswith("{")

    def node_spec(self, view_type: str | None, kind: str) -> NodeSpec | None:
        if kind in self.patch_nodes:
            return self.patch_nodes[kind]
        if view_type is not None:
            spec = self.types.get(view_type)
            return spec.nodes.get(kind) if spec else None
        # an inheritance spec carries no view type: any type's vocabulary is admissible
        for spec in self.types.values():
            if kind in spec.nodes:
                return spec.nodes[kind]
        return None

    def attr_type(self, view_type: str | None, kind: str, attr: str) -> AttrType | None:
        node_tables = (
            [
                spec.nodes[kind].attrs
                for spec in self.types.values()
                if kind in spec.nodes
            ]
            if view_type is None and kind not in self.patch_nodes
            else [spec.attrs for spec in (self.node_spec(view_type, kind),) if spec]
        )
        for table in (
            *node_tables,
            self.html_attrs if self.is_html(kind) else {},
            self.common_attrs,
            self.patch_attrs,
        ):
            found = _resolve_attribute_type(table, attr)
            if found is not None:
                return found
        return None


def _resolve_attribute_type(table: dict[str, AttrType], attr: str) -> AttrType | None:
    if attr in table:
        return table[attr]
    head, dash, _rest = attr.partition("-")
    if dash and f"{head}-*" in table:
        return table[f"{head}-*"]
    return None


@cache
def schema() -> Schema:
    with _debug.perf("schema_load", path=str(SCHEMA_PATH)) as span:
        with SCHEMA_PATH.open(encoding="utf-8") as handle:
            loaded = Schema(json.load(handle))
        span.set(
            version=loaded.version,
            types=len(loaded.types),
            kinds=sum(len(t.nodes) for t in loaded.types.values()),
            attrs=sum(
                len(n.attrs) for t in loaded.types.values() for n in t.nodes.values()
            ),
        )
    _debug.lifecycle("schema_loaded", version=loaded.version, types=len(loaded.types))
    return loaded
