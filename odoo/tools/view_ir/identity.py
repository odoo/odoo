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


def identify(root: Node) -> dict[str, Node]:
    """Give every node of ``root`` a stable id and return ``{id: node}``.

    Derivation, in order:

    1. an explicit ``id`` attribute is the id;
    2. a named node (``name=``) is ``kind:name`` — ``field:partner_id``,
       ``button:action_confirm``, ``page:other_info``;
    3. a kind that occurs once in the view is the kind — ``sheet``, ``header``;
    4. anything else is ``kind@hash`` over the parent's id and the node's own
       kind and attributes — not its children, so an anonymous ``<group>``
       keeps its id when its content changes or its siblings move, and loses
       it when it is re-parented or its attributes change; two such siblings
       that are alike are told apart by document order (``#2``).

    Ids are still unique when two nodes claim the same one — a field placed
    twice, an HTML ``id`` an arch repeats: the second and later carry ``#2``,
    ``#3``, … in document order, explicit ids claiming before derived ones.
    """
    # one walk, document order, each node with its parent
    nodes: list[tuple[Node, Node | None]] = []
    stack: list[tuple[Node, Node | None]] = [(root, None)]
    while stack:
        node, parent = stack.pop()
        nodes.append((node, parent))
        stack.extend((child, node) for child in reversed(node.children))

    counts: dict[str, int] = {}
    for node, _parent in nodes:
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
    for node, _parent in nodes:
        if node.attrs.get("id"):
            node.id = claim(node.attrs["id"], node)

    # a parent precedes its children in document order, so its id is settled
    for node, parent in nodes:
        if node.attrs.get("id"):
            continue
        if node.attrs.get("name"):
            node.id = claim(f"{node.kind}:{node.attrs['name']}", node)
        elif counts[node.kind] == 1:
            node.id = claim(node.kind, node)
        else:
            digest = _short_hash(
                [
                    parent.id or "" if parent is not None else "",
                    node.kind,
                    *(f"{key}={value}" for key, value in sorted(node.attrs.items())),
                ]
            )
            node.id = claim(f"{node.kind}@{digest}", node)
    return ids
