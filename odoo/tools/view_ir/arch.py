from __future__ import annotations

import json

from lxml import etree

from odoo.libs.debug_log import DebugLog

from .node import COMMENT, MARKUP_KINDS, PROCESSING_INSTRUCTION, Node

_debug = DebugLog(__name__)


def from_arch(element: etree._Element) -> Node:
    with _debug.perf("from_arch", kind=element.tag) as span:
        node = _from_element(element, {})
        if _debug.perf.enabled:
            span.set(nodes=sum(1 for _ in node.walk()))
    return node


def _from_element(element: etree._Element, inherited: dict[str | None, str]) -> Node:
    declared = {
        prefix: uri
        for prefix, uri in element.nsmap.items()
        if inherited.get(prefix) != uri
    }
    node = Node(
        kind=element.tag,
        attrs=dict(element.attrib),
        text=element.text,
        tail=element.tail,
        nsmap=declared or None,
        line=element.sourceline,
    )
    scope = {**inherited, **declared}
    for child in element:
        if isinstance(child.tag, str):
            node.children.append(_from_element(child, scope))
        elif isinstance(child, etree._Comment):
            node.children.append(
                Node(COMMENT, text=child.text, tail=child.tail, line=child.sourceline)
            )
        elif isinstance(child, etree._ProcessingInstruction):
            node.children.append(
                Node(
                    PROCESSING_INSTRUCTION,
                    attrs={"target": child.target},
                    text=child.text,
                    tail=child.tail,
                    line=child.sourceline,
                )
            )
        elif child.tail:
            if node.children:
                node.children[-1].tail = (node.children[-1].tail or "") + child.tail
            else:
                node.text = (node.text or "") + child.tail
    return node


def to_arch(node: Node) -> etree._Element:
    with _debug.perf("to_arch", kind=node.kind) as span:
        element = _to_element(node, None)
        if _debug.perf.enabled:
            span.set(nodes=sum(1 for _ in element.iter()))
    return element


def _to_element(node: Node, parent: etree._Element | None) -> etree._Element:
    if node.kind == COMMENT:
        element = etree.Comment(node.text)
    elif node.kind == PROCESSING_INSTRUCTION:
        element = etree.ProcessingInstruction(node.attrs["target"], node.text)
    elif parent is None:
        element = etree.Element(node.kind, node.attrs, nsmap=node.nsmap)
    else:
        element = etree.SubElement(parent, node.kind, node.attrs, nsmap=node.nsmap)
    if node.kind in MARKUP_KINDS:
        if parent is None:
            raise ValueError(f"a {node.kind} node cannot be the root of an arch")
        parent.append(element)
    else:
        element.text = node.text
    element.tail = node.tail
    if node.line is not None:
        # the line a view error points at: an element the IR materialises
        # answers for the arch line it was read from
        element.sourceline = node.line
    for child in node.children:
        _to_element(child, element)
    return element


def from_string(arch: str | bytes) -> Node:
    return from_arch(etree.fromstring(arch))


def to_string(node: Node) -> str:
    return etree.tostring(to_arch(node), encoding="unicode")


def to_json(node: Node) -> str:
    payload = json.dumps(node.to_dict(), ensure_ascii=False, separators=(",", ":"))
    _debug.pipeline("to_json", kind=node.kind, chars=len(payload))
    return payload


def from_json(payload: str | bytes) -> Node:
    node = Node.from_dict(json.loads(payload))
    _debug.pipeline("from_json", kind=node.kind, chars=len(payload))
    return node


def canonical(element: etree._Element) -> bytes:
    return etree.tostring(element, method="c14n", with_comments=True)
