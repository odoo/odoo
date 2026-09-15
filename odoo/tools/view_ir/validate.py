from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

from odoo.libs.debug_log import DebugLog

from .node import Node
from .schema import Schema, schema

_debug = DebugLog(__name__)

BOOL_LITERALS = frozenset({"1", "0", "True", "False", "true", "false"})
# convert.py substitutes %(module.xmlid)d with the record id before the arch is stored
XMLID_REF = re.compile(r"%\((.*?)\)[ds]")
REQUIRED_ATTRS: dict[str, tuple[str, ...]] = {
    "field": ("name",),
    "xpath": ("expr",),
    "filter": ("name",),
}


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    path: tuple[int, ...]
    kind: str
    detail: str
    severity: str = "error"

    def __str__(self) -> str:
        where = "/".join(map(str, self.path)) or "root"
        return f"{self.severity} {self.code} at {self.kind}[{where}]: {self.detail}"


def get_issues(
    node: Node, view_type: str | None = None, *, spec: Schema | None = None
) -> list[Issue]:
    spec = spec or schema()
    if view_type is None:
        view_type = spec.view_type_of(node.kind)
        _debug.logic("view_type_inferred", root=node.kind, view_type=view_type)
    with _debug.perf("validate", kind=node.kind, view_type=view_type) as span:
        issues = list(_iter_node_issues(node, view_type, spec, ()))
        if _debug.perf.enabled:
            span.set(
                nodes=sum(1 for _ in node.walk()),
                errors=sum(i.severity == "error" for i in issues),
                warnings=sum(i.severity == "warning" for i in issues),
            )
    if _debug.logic.enabled:
        for issue in issues:
            _debug.logic(
                "issue",
                code=issue.code,
                severity=issue.severity,
                kind=issue.kind,
                path="/".join(map(str, issue.path)) or "root",
                detail=issue.detail,
            )
    return issues


def _iter_node_issues(
    node: Node, view_type: str | None, spec: Schema, path: tuple[int, ...]
) -> Iterator[Issue]:
    if node.is_markup:
        return
    node_spec = spec.node_spec(view_type, node.kind)
    if node_spec is None and not spec.is_html(node.kind):
        yield Issue(
            "unknown-kind",
            path,
            node.kind,
            f"no node kind {node.kind!r} in {view_type!r}",
        )
    for attr in REQUIRED_ATTRS.get(node.kind, ()):
        if attr not in node.attrs:
            yield Issue("missing-attr", path, node.kind, f"{attr!r} is required")
    for attr, value in node.attrs.items():
        attr_type = spec.attr_type(view_type, node.kind, attr)
        if attr_type is None:
            yield Issue("unknown-attr", path, node.kind, attr, "warning")
            continue
        problem = _get_value_error(attr_type, value)
        if problem:
            yield Issue(f"bad-{problem}", path, node.kind, f"{attr}={value!r}")
    if node_spec is not None and node_spec.children is not None:
        for index, child in enumerate(node.children):
            if child.is_markup:
                continue
            child_kind = "html" if spec.is_html(child.kind) else child.kind
            if spec.node_spec(view_type, child.kind) is None and child_kind != "html":
                continue
            if child_kind not in node_spec.children:
                yield Issue(
                    "unexpected-child",
                    (*path, index),
                    child.kind,
                    f"not expected under {node.kind!r}",
                    "warning",
                )
    for index, child in enumerate(node.children):
        yield from _iter_node_issues(child, view_type, spec, (*path, index))


def _get_value_error(attr_type: str | list[str], value: str) -> str | None:
    if isinstance(attr_type, list):
        return None if value in attr_type else "enum"
    match attr_type:
        case "bool":
            return None if value in BOOL_LITERALS else "bool"
        case "int":
            return None if value.lstrip("-").isdigit() else "int"
        case "pyexpr" | "domain" | "context" | "json":
            return None if _is_valid_expression(value) else attr_type
        case _:
            return None


def _is_valid_expression(expression: str) -> bool:
    try:
        ast.parse(XMLID_REF.sub("0", expression).strip() or "None", mode="eval")
    except SyntaxError:
        return False
    return True
