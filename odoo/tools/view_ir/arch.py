from __future__ import annotations

import json

from lxml import etree

from .node import Node


def from_arch(element: etree._Element) -> Node:
    return _from_element(element, {})


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
    )
    scope = {**inherited, **declared}
    node.children = [
        _from_element(child, scope) for child in element if isinstance(child.tag, str)
    ]
    return node


def to_arch(node: Node) -> etree._Element:
    return _to_element(node, None)


def _to_element(node: Node, parent: etree._Element | None) -> etree._Element:
    if parent is None:
        element = etree.Element(node.kind, node.attrs, nsmap=node.nsmap)
    else:
        element = etree.SubElement(parent, node.kind, node.attrs, nsmap=node.nsmap)
    element.text = node.text
    element.tail = node.tail
    for child in node.children:
        _to_element(child, element)
    return element


def from_string(arch: str | bytes) -> Node:
    return from_arch(etree.fromstring(arch))


def to_string(node: Node) -> str:
    return etree.tostring(to_arch(node), encoding="unicode")


def to_json(node: Node) -> str:
    return json.dumps(node.to_dict(), ensure_ascii=False, separators=(",", ":"))


def from_json(payload: str | bytes) -> Node:
    return Node.from_dict(json.loads(payload))


def canonical(element: etree._Element) -> bytes:
    return etree.tostring(element, method="c14n", with_comments=False)
