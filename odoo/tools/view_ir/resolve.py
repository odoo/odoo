from __future__ import annotations

import copy
import re

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
            try:
                work.root = apply(work.root, [copy.deepcopy(patch)]).root
            except ValueError:
                # a change the merge refuses (a bad separator, say): the XML
                # path applies the same spec and reports it in its own words
                out.extend(flat[index:])
                break
            out.append(patch)
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


SIMPLE_XPATH = re.compile(
    r"^//(?P<tag>[A-Za-z_][\w.-]*)"
    r"(?:\[@(?P<attr>[A-Za-z_][\w.-]*)=(?P<q>['\"])(?P<value>[^'\"]*)(?P=q)\])?$"
)


class _Working:
    """The tree as the specs so far leave it, materialised on demand for xpath."""

    def __init__(self, root: Node) -> None:
        self.root = root
        self._arch: etree._Element | None = None
        self._nodes: dict[etree._Element, Node] | None = None
        self._ids: dict[str, Node] | None = None

    def invalidate(self) -> None:
        self._arch = None
        self._nodes = None
        self._ids = None

    def ids(self) -> dict[str, Node]:
        if self._ids is None:
            self._ids = identify(self.root)
        return self._ids

    def locate(self, spec: etree._Element) -> Node | None:
        """The node a spec addresses — off the ids for the shapes that name
        one node (`<field name="x">`, `//tag`, `//tag[@attr='v']`, the
        overwhelming majority), off the materialised arch's xpath otherwise,
        both with the XML combine's first-match rule."""
        ids = self.ids()
        tag, attr, value = _simple_target(spec)
        if tag is not None:
            if attr == "name" and value:
                named = ids.get(f"{tag}:{value}")
                # a node under an explicit html id has no `kind:name` entry,
                # and an explicit id spelled `kind:name` is not that node:
                # both fall through to the scan the XML locate does
                if (
                    named is not None
                    and named.kind == tag
                    and named.attrs.get("name") == value
                ):
                    return named
            if attr is None:
                return next(self.root.find(tag), None)
            return next(
                (node for node in self.root.find(tag) if node.attrs.get(attr) == value),
                None,
            )
        target = locate_node(self.arch(), spec)
        return None if target is None else self.node_of(target)

    def arch(self) -> etree._Element:
        if self._arch is None:
            self.ids()
            self._arch = to_arch(self.root)
            elements = list(self._arch.iter())
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


def _simple_target(
    spec: etree._Element,
) -> tuple[str | None, str | None, str | None]:
    """(tag, attr, value) when the spec names its target by one attribute or
    by tag alone; (None, None, None) when only xpath can say."""
    if spec.tag != "xpath":
        attrs = [(k, v) for k, v in spec.attrib.items() if k != "position"]
        if spec.tag == "field":
            return "field", "name", spec.get("name")
        if not attrs:
            return spec.tag, None, None
        if len(attrs) == 1:
            return spec.tag, attrs[0][0], attrs[0][1]
        return None, None, None
    match = SIMPLE_XPATH.match((spec.get("expr") or "").strip())
    if not match:
        return None, None, None
    return match.group("tag"), match.group("attr"), match.group("value")


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
    target_node = work.locate(spec)
    if target_node is None:
        return None
    target_id = target_node.id
    assert target_id is not None
    if op == "attributes":
        changes = []
        # every <attribute> under the spec, wrapped or not, as the XML combine
        # reads them (`spec.iter("attribute")`): a wrapper says nothing there
        for attribute in spec.iter("attribute"):
            name = attribute.get("name")
            # a malformed <attribute> is the XML path's to refuse, with its
            # message: an unknown attribute, add/remove beside text
            if (
                not name
                or any(
                    key not in ("name", "add", "remove", "separator")
                    and not key.startswith("data-oe-")
                    for key in attribute.attrib
                )
                or (
                    (attribute.get("add") or attribute.get("remove")) and attribute.text
                )
            ):
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
            moved = work.locate(child)
            if moved is None or len(child):
                return None
            assert moved.id is not None
            content.append(Move(moved.id))
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
