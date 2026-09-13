from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Node:
    kind: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    text: str | None = None
    tail: str | None = None
    nsmap: dict[str | None, str] | None = None

    def walk(
        self, path: tuple[int, ...] = ()
    ) -> Iterator[tuple[tuple[int, ...], Node]]:
        yield path, self
        for index, child in enumerate(self.children):
            yield from child.walk((*path, index))

    def find(self, kind: str) -> Iterator[Node]:
        for _path, node in self.walk():
            if node.kind == kind:
                yield node

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind}
        if self.attrs:
            out["attrs"] = dict(self.attrs)
        if self.text is not None:
            out["text"] = self.text
        if self.tail is not None:
            out["tail"] = self.tail
        if self.nsmap:
            out["nsmap"] = {prefix or "": uri for prefix, uri in self.nsmap.items()}
        if self.children:
            out["children"] = [child.to_dict() for child in self.children]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        nsmap = data.get("nsmap")
        return cls(
            kind=data["kind"],
            attrs=dict(data.get("attrs") or {}),
            children=[cls.from_dict(child) for child in data.get("children") or ()],
            text=data.get("text"),
            tail=data.get("tail"),
            nsmap={prefix or None: uri for prefix, uri in nsmap.items()}
            if nsmap
            else None,
        )
