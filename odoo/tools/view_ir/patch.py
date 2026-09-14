from __future__ import annotations

import copy
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from odoo.libs.xml import merge_attribute_value

from .identity import identify
from .node import Node

Op = Literal[
    "replace", "replace_inner", "before", "after", "inside", "attributes", "remove"
]


class PatchError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Move:
    """A node of the base, addressed by id, placed where this item sits."""

    target: str


@dataclass(frozen=True, slots=True)
class AttrChange:
    name: str
    value: str | None = None
    add: str = ""
    remove: str = ""
    separator: str | None = None


@dataclass(frozen=True, slots=True)
class Patch:
    op: Op
    target: str
    content: tuple[Node | Move, ...] = ()
    attributes: tuple[AttrChange, ...] = ()
    origin: str | None = None
    # text inserted at the insertion point ahead of the content — the leading
    # text of an XML spec ("Do you confirm … <strong>…</strong>")
    text: str | None = None


@dataclass(slots=True)
class Conflict:
    target: str
    attribute: str
    origins: tuple[str | None, str | None]


@dataclass(slots=True)
class Applied:
    root: Node
    managed: dict[tuple[str, str], str | None] = field(default_factory=dict)
    conflicts: list[Conflict] = field(default_factory=list)


def _parent_of(root: Node, target: Node) -> tuple[Node, int]:
    for _path, node in root.walk():
        for index, child in enumerate(node.children):
            if child is target:
                return node, index
    raise PatchError(f"node {target.id!r} has no parent")


def _stamp(nodes: Iterable[Node], origin: str | None) -> None:
    for node in nodes:
        for _path, descendant in node.walk():
            if descendant.origin is None:
                descendant.origin = origin


def apply(root: Node, patches: Iterable[Patch]) -> Applied:
    """Apply ``patches`` to ``root`` in order and return the result.

    Every patch addresses a node by the id it has *after* the patches before
    it — ids are re-derived after each one, as an xpath is evaluated against
    the arch the previous specs left. The semantics are those of the XML
    specs: ``replace`` swaps the target for the content (``$0`` in the content
    is the target itself), ``replace_inner`` swaps its children, ``before`` /
    ``after`` / ``inside`` insert around or into it, ``attributes`` edits its
    attributes with the add/remove/separator rules of ``<attribute>``, and
    ``remove`` drops it. A :class:`Move` in the content takes a node of the
    base out of its place and puts it there.

    Provenance: a node the patches insert carries the patch's ``origin``; the
    last origin to set each attribute is kept in ``managed``, and an attribute
    set by two different origins is a :class:`Conflict` — reported, not
    refused, so the caller decides.
    """
    result = Applied(root=root)
    ids = identify(root)
    for patch in patches:
        target = ids.get(patch.target)
        if target is None:
            raise PatchError(
                f"patch {patch.op!r} from {patch.origin!r}: no node {patch.target!r}"
            )
        if patch.op == "attributes":
            _apply_attributes(result, target, patch)
        elif patch.op == "remove":
            if target is result.root:
                raise PatchError("the root cannot be removed")
            parent, index = _parent_of(result.root, target)
            del parent.children[index]
        else:
            content = _materialise(result.root, ids, patch, target)
            if patch.op == "inside":
                _insert(target, len(target.children), content, patch.text)
            elif patch.op == "replace_inner":
                target.children = []
                _insert(target, 0, content, patch.text)
            elif target is result.root:
                if patch.op != "replace":
                    raise PatchError("only `replace` applies to the root")
                if len(content) != 1:
                    raise PatchError("replacing the root takes exactly one node")
                result.root = content[0]
            else:
                parent, index = _parent_of(result.root, target)
                if patch.op == "replace":
                    del parent.children[index]
                    _insert(parent, index, content, None)
                elif patch.op == "before":
                    _insert(parent, index, content, patch.text)
                else:
                    _insert(parent, index + 1, content, patch.text)
        ids = identify(result.root)
    return result


def _insert(parent: Node, index: int, content: list[Node], text: str | None) -> None:
    """Place ``content`` at ``index`` under ``parent``, ``text`` ahead of it —
    on the tail of the node before the insertion point, or the parent's text."""
    if text:
        # as the XML combine does: the text before the point loses its
        # trailing whitespace, the spec's text carries its own
        if index:
            previous = parent.children[index - 1]
            previous.tail = (previous.tail or "").rstrip() + text
        else:
            parent.text = (parent.text or "").rstrip() + text
    parent.children[index:index] = content


def _materialise(
    root: Node, ids: dict[str, Node], patch: Patch, target: Node
) -> list[Node]:
    content: list[Node] = []
    for item in patch.content:
        if isinstance(item, Move):
            moved = ids.get(item.target)
            if moved is None:
                raise PatchError(
                    f"patch {patch.op!r} from {patch.origin!r}: "
                    f"nothing to move at {item.target!r}"
                )
            parent, index = _parent_of(root, moved)
            del parent.children[index]
            content.append(moved)
        else:
            # the patch's own nodes carry its origin; a moved node keeps its
            # provenance, and so does the replaced node `$0` puts back
            _stamp((item,), patch.origin)
            content.append(item)
    return [_place_target(node, patch, target) for node in content]


def _place_target(node: Node, patch: Patch, target: Node) -> Node:
    """`$0` anywhere in the content stands for a copy of the replaced node,
    as the `$0` text of an XML spec does — a copy, so two placeholders do not
    share one node."""
    if node.kind == "$0":
        if patch.op != "replace":
            raise PatchError("`$0` stands for the replaced node only")
        return copy.deepcopy(target)
    node.children = [_place_target(child, patch, target) for child in node.children]
    return node


def _apply_attributes(result: Applied, target: Node, patch: Patch) -> None:
    for change in patch.attributes:
        if change.add or change.remove:
            if change.value:
                raise PatchError(
                    f"attribute {change.name!r}: add/remove and a value are exclusive"
                )
            value = merge_attribute_value(
                change.name,
                target.attrs.get(change.name, ""),
                change.add,
                change.remove,
                change.separator,
            )
        else:
            value = change.value or ""
        key = (target.id or "", change.name)
        previous = result.managed.get(key, target.origin)
        if key in result.managed and previous != patch.origin:
            result.conflicts.append(
                Conflict(target.id or "", change.name, (previous, patch.origin))
            )
        result.managed[key] = patch.origin
        if value:
            target.attrs[change.name] = value
        else:
            target.attrs.pop(change.name, None)
