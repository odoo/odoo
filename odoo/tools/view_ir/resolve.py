from __future__ import annotations

import copy

from lxml import etree

from odoo.libs.xml import SKIPPED_ELEMENT_TYPES, apply_inheritance_specs, locate_node

from .arch import from_arch, to_arch
from .identity import identify
from .node import Node
from .patch import AttrChange, Move, Op, Patch, apply

POSITIONS: dict[str, Op] = {
    "inside": "inside",
    "before": "before",
    "after": "after",
    "attributes": "attributes",
}
REPLACE_MODES: dict[str, Op] = {"outer": "replace", "inner": "replace_inner"}


def translate_specs(
    root: Node, specs_tree: etree._Element, origin: str | None = None
) -> list[Patch | etree._Element]:
    """The XML inheritance specs of one view as id-addressed patches on ``root``.

    Each spec's target is located the way the XML combine locates it — the
    same xpath, the same first match — on the arch ``root`` materialises to,
    and named by the id ``identify()`` derives for that node. A spec whose
    target cannot be located, whose content holds a ``$0`` in a text node
    beside other text, or whose position is not one of the five, stays an
    element: the caller applies it the XML way. Patches address the tree
    the specs before them leave, so translation walks the specs in order and
    applies each translated patch to a working copy as it goes.
    """
    # the working tree is a copy, and so is what goes into it: the caller
    # gets `root` untouched and patches whose nodes belong to no tree yet
    work = _Working(copy.deepcopy(root))
    out: list[Patch | etree._Element] = []
    flat = _flatten(specs_tree)
    for index, spec in enumerate(flat):
        patch = _translate(work, spec, origin)
        if patch is None:
            out.append(spec)
            try:
                work.apply_xml(copy.deepcopy(spec))
            except ValueError:
                # the XML path will report it; what follows cannot be placed
                out.extend(flat[index + 1 :])
                break
        else:
            out.append(patch)
            work.root = apply(work.root, [copy.deepcopy(patch)]).root
            work.invalidate()
    return out


def _flatten(specs_tree: etree._Element) -> list[etree._Element]:
    specs = [specs_tree] if specs_tree.tag != "data" else list(specs_tree)
    flat: list[etree._Element] = []
    while specs:
        spec = specs.pop(0)
        if isinstance(spec, SKIPPED_ELEMENT_TYPES):
            continue
        if spec.tag == "data":
            specs[0:0] = list(spec)
            continue
        flat.append(spec)
    return flat


class _Working:
    """The tree as the specs so far leave it, materialised on demand for xpath."""

    def __init__(self, root: Node) -> None:
        self.root = root
        self._arch: etree._Element | None = None
        self._nodes: dict[etree._Element, Node] | None = None

    def invalidate(self) -> None:
        self._arch = None
        self._nodes = None

    def arch(self) -> etree._Element:
        if self._arch is None:
            identify(self.root)
            self._arch = to_arch(self.root)
            elements = [el for el in self._arch.iter() if isinstance(el.tag, str)]
            nodes = [node for _path, node in self.root.walk()]
            self._nodes = dict(zip(elements, nodes, strict=True))
        return self._arch

    def node_of(self, element: etree._Element) -> Node:
        self.arch()
        assert self._nodes is not None
        return self._nodes[element]

    def apply_xml(self, spec: etree._Element) -> None:
        arch = apply_inheritance_specs(self.arch(), spec)
        self.root = from_arch(arch)
        self.invalidate()


def _translate(
    work: _Working, spec: etree._Element, origin: str | None
) -> Patch | None:
    position = spec.get("position", "inside")
    op = (
        REPLACE_MODES.get(spec.get("mode", "outer"))
        if position == "replace"
        else POSITIONS.get(position)
    )
    if op is None:
        return None
    target = locate_node(work.arch(), spec)
    if target is None:
        return None
    target_id = work.node_of(target).id
    assert target_id is not None
    if op == "attributes":
        changes = []
        for attribute in spec.iterchildren("attribute"):
            name = attribute.get("name")
            if not name or (attribute.get("add") is not None and attribute.text):
                return None
            changes.append(
                AttrChange(
                    name,
                    value=None
                    if attribute.get("add") or attribute.get("remove")
                    else (attribute.text or ""),
                    add=attribute.get("add", ""),
                    remove=attribute.get("remove", ""),
                    separator=attribute.get("separator"),
                )
            )
        return Patch(op, target_id, attributes=tuple(changes), origin=origin)
    text = spec.text if spec.text and spec.text.strip() else None
    if text and op in ("replace", "replace_inner"):
        return None
    content: list[Node | Move] = []
    for child in spec:
        if not isinstance(child.tag, str):
            continue
        if child.get("position") == "move":
            moved = locate_node(work.arch(), child)
            if moved is None or len(child):
                return None
            moved_id = work.node_of(moved).id
            assert moved_id is not None
            content.append(Move(moved_id))
            continue
        node = _content_node(child, op)
        if node is None:
            return None
        content.append(node)
    return Patch(op, target_id, content=tuple(content), origin=origin, text=text)


def _content_node(element: etree._Element, op: str) -> Node | None:
    node = from_arch(element)
    if not _place_dollar_zero(node, op):
        return None
    return node


def _place_dollar_zero(node: Node, op: str) -> bool:
    """`$0` as a node's whole text becomes a `$0` child, as in a replace spec;
    `$0` anywhere else is left to the XML path."""
    if node.text is not None and "$0" in node.text:
        if node.text != "$0" or op != "replace":
            return False
        node.text = None
        node.children.append(Node("$0"))
    for child in node.children:
        if child.tail and "$0" in child.tail:
            return False
        if not _place_dollar_zero(child, op):
            return False
    return True
