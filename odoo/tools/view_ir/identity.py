from __future__ import annotations

from collections.abc import Iterable
from hashlib import blake2b

from .node import Node


def _short_hash(parts: Iterable[str]) -> str:
    digest = blake2b(digest_size=6)
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()


def _signature(node: Node) -> str:
    # the node's own kind and attributes, not its children: an overlay that
    # adds a field to an anonymous group must not change the group's id,
    # or the next overlay's address is stale
    return _short_hash(
        [node.kind, *(f"{key}={value}" for key, value in sorted(node.attrs.items()))]
    )


def identify(root: Node) -> dict[str, Node]:
    """Give every node of ``root`` a stable id and return ``{id: node}``.

    Derivation, in order:

    1. an explicit ``id`` attribute is the id;
    2. a named node (``name=``) is ``kind:name`` — ``field:partner_id``,
       ``button:action_confirm``, ``page:other_info``;
    3. a kind that occurs once in the view is the kind — ``sheet``, ``header``;
    4. anything else is ``kind@hash`` over the parent's id and the node's own
       kind and attributes — so an anonymous ``<group>`` keeps its id when
       its content changes or its siblings move, and loses it when it is
       re-parented or its attributes change; two such siblings that are
       alike are told apart by document order (``#2``).

    Ids are still unique when two nodes claim the same one — a field placed
    twice, an HTML ``id`` an arch repeats: the second and later carry ``#2``,
    ``#3``, … in document order, explicit ids claiming before derived ones.
    """
    counts: dict[str, int] = {}
    for _path, node in root.walk():
        counts[node.kind] = counts.get(node.kind, 0) + 1

    ids: dict[str, Node] = {}
    taken: dict[str, int] = {}

    def claim(base: str, node: Node) -> str:
        n = taken.get(base, 0) + 1
        taken[base] = n
        node_id = base if n == 1 else f"{base}#{n}"
        ids[node_id] = node
        return node_id

    # explicit ids first, in document order, so a derived id never takes one
    for _path, node in root.walk():
        if node.attrs.get("id"):
            node.id = claim(node.attrs["id"], node)

    def visit(node: Node, parent_id: str | None) -> None:
        if node.attrs.get("id"):
            node_id = node.id
        elif node.attrs.get("name"):
            node_id = claim(f"{node.kind}:{node.attrs['name']}", node)
        elif counts[node.kind] == 1:
            node_id = claim(node.kind, node)
        else:
            node_id = claim(
                f"{node.kind}@{_short_hash([parent_id or '', _signature(node)])}",
                node,
            )
        node.id = node_id
        for child in node.children:
            visit(child, node_id)

    visit(root, None)
    return ids
