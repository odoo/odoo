from __future__ import annotations

import copy
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from odoo.libs.xml import merge_attribute_value

from .identity import identify
from .node import Node

Op = Literal[
    "replace", "replace_inner", "before", "after", "inside", "attributes", "remove"
]


_INDENTATION = re.compile(r"\n[ \t]*$")


class PatchError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Move:
    target: str
    tail: str | None = None


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
    one origin sets over another's value is a :class:`Conflict` — reported,
    not refused, so the caller decides; an add/remove composes and is none.
    """
    result = Applied(root=root)
    for patch in patches:
        apply_one(result, patch, identify(result.root))
    return result


def apply_one(result: Applied, patch: Patch, ids: dict[str, Node]) -> None:
    """One patch onto ``result.root``, addressed through ``ids`` — the ids of
    ``result.root`` as it stands (:func:`identify`). ``result`` accumulates
    ``managed`` and ``conflicts`` across calls, so a caller that applies one
    view's patches after another's sees the attribute two views both set.
    A refused patch leaves the tree as it was."""
    target = ids.get(patch.target)
    if target is None:
        raise PatchError(
            f"patch {patch.op!r} from {patch.origin!r}: no node {patch.target!r}"
        )
    if patch.op == "attributes":
        _apply_attributes(result, target, patch)
        return
    if patch.op == "remove":
        if target is result.root:
            raise PatchError("the root cannot be removed")
        parent, index = _parent_of(result.root, target)
        del parent.children[index]
        return
    if target is result.root and patch.op not in ("inside", "replace_inner"):
        if patch.op != "replace":
            raise PatchError("only `replace` applies to the root")
        if len(patch.content) != 1:
            raise PatchError("replacing the root takes exactly one node")
    content = _materialise(result.root, ids, patch, target)
    if patch.op == "inside":
        _insert(target, len(target.children), content, patch.text)
    elif patch.op == "replace_inner":
        # the XML combine drops the node's text with its children
        target.children = []
        target.text = None
        _insert(target, 0, content, patch.text)
    elif target is result.root:
        result.root = content[0]
        # the XML combine carries the template name over
        if "t-name" in target.attrs and "t-name" not in result.root.attrs:
            result.root.attrs["t-name"] = target.attrs["t-name"]
    else:
        parent, index = _parent_of(result.root, target)
        if patch.op == "replace":
            # as the XML combine: the content takes the node's place, its
            # tail goes with it, the text before is left alone
            parent.children[index : index + 1] = content
        elif patch.op == "before":
            _insert(parent, index, content, patch.text)
        else:
            # what followed the target follows the content now
            trailing = target.tail
            target.tail = None
            _insert(parent, index + 1, content, patch.text)
            last = content[-1] if content else target
            last.tail = (last.tail or "") + (trailing or "") or None


def _insert(parent: Node, index: int, content: list[Node], text: str | None) -> None:
    """Place ``content`` at ``index`` under ``parent``, ``text`` ahead of it.

    As the XML combine's ``add_stripped_items_before``: the text before the
    insertion point (the previous node's tail, or the parent's text) loses
    its trailing whitespace and gains ``text``; that whitespace reappears
    after the inserted content, so the indentation the arch had is kept.
    """
    if index:
        previous = parent.children[index - 1]
        before = previous.tail or ""
    else:
        before = parent.text or ""
    stripped = before.rstrip()
    indentation = _INDENTATION.search(before)
    trailing = indentation.group(0) if indentation else ""
    joined = (stripped + (text or "")) if (text is not None or trailing) else before
    if index:
        parent.children[index - 1].tail = joined or None
    else:
        parent.text = joined or None
    parent.children[index:index] = content
    if content:
        # the last node's own trailing whitespace goes, the indentation the
        # insertion point had takes its place -- even when there was none
        last = content[-1]
        last.tail = ((last.tail or "").rstrip() + trailing) or None


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
            # as the XML combine's remove_element: what followed the node
            # stays where it was, the node carries the placeholder's tail
            _leave_tail(parent, index)
            del parent.children[index]
            # an outer replace's extract hands the node over bare
            moved.tail = None if patch.op == "replace" else item.tail
            content.append(moved)
        else:
            # the patch's own nodes carry its origin; a moved node keeps its
            # provenance, and so does the replaced node `$0` puts back
            _stamp((item,), patch.origin)
            content.append(item)
    return [_place_target(node, patch, target) for node in content]


def _leave_tail(parent: Node, index: int) -> None:
    tail = parent.children[index].tail
    if not tail:
        return
    if index:
        previous = parent.children[index - 1]
        previous.tail = (previous.tail or "") + tail
    else:
        parent.text = (parent.text or "") + tail


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
    # every value first, so a change the merge refuses leaves the node as it was
    attrs = dict(target.attrs)
    for change in patch.attributes:
        if change.add or change.remove:
            if change.value:
                raise PatchError(
                    f"attribute {change.name!r}: add/remove and a value are exclusive"
                )
            value = merge_attribute_value(
                change.name,
                attrs.get(change.name, ""),
                change.add,
                change.remove,
                change.separator,
            )
        else:
            value = change.value or ""
        if value:
            attrs[change.name] = value
        else:
            attrs.pop(change.name, None)
    for change in patch.attributes:
        key = (target.id or "", change.name)
        previous = result.managed.get(key, target.origin)
        # an add/remove composes with what is there; only a value set over
        # another origin's value is a conflict
        if (
            key in result.managed
            and previous != patch.origin
            and not (change.add or change.remove)
        ):
            result.conflicts.append(
                Conflict(target.id or "", change.name, (previous, patch.origin))
            )
        result.managed[key] = patch.origin
    target.attrs = attrs
