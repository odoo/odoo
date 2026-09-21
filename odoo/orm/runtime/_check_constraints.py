"""Evaluating the CHECK constraints this tier can model.

PostgreSQL refuses a row whose CHECK evaluates to FALSE. A CHECK that
evaluates to NULL -- unknown -- passes, which is why every comparison against
a NULL column here answers `None` rather than False. Anything this grammar
cannot parse answers `None` too, so the twin never refuses a row the database
would accept: it enforces what it can model and ignores the rest, exactly as
the `unique(...)` handling does.

Grammar, which covers the shapes that exist in this workspace (293 of 341
table CHECKs are a simple comparison or a boolean combination of them):

    expr      := term (OR term)*
    term      := factor (AND factor)*
    factor    := NOT factor | '(' expr ')' | predicate
    predicate := operand (cmp operand | IS [NOT] NULL | [NOT] IN '(' operands ')')
    operand   := identifier | number | string
"""

from __future__ import annotations

import re
import typing

_TOKEN = re.compile(
    r"""
    \s*(?:
      (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<comma>,)
    | (?P<cmp><=|>=|<>|!=|=|<|>)
    | (?P<number>-?\d+\.\d+|-?\d+)
    | (?P<string>'(?:[^']|'')*')
    | (?P<name>"[^"]+"|[A-Za-z_][A-Za-z_0-9]*)
    )
    """,
    re.VERBOSE,
)

_KEYWORDS = {"AND", "OR", "NOT", "IS", "NULL", "IN", "TRUE", "FALSE"}


class _Unparsable(Exception):
    pass


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(text):
        if text[position].isspace():
            position += 1
            continue
        match = _TOKEN.match(text, position)
        if match is None or match.end() == position:
            raise _Unparsable(text[position:])
        position = match.end()
        kind = match.lastgroup
        if kind is None:
            raise _Unparsable(text[position:])
        value = match.group(kind)
        if kind == "name":
            bare = value.strip('"')
            kind = "keyword" if bare.upper() in _KEYWORDS else "name"
            value = bare.upper() if kind == "keyword" else bare
        tokens.append((kind, value))
    return tokens


class _Parser:
    __slots__ = ("_at", "_tokens")

    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self._tokens = tokens
        self._at = 0

    def _peek(self) -> tuple[str, str] | None:
        return self._tokens[self._at] if self._at < len(self._tokens) else None

    def _take(self) -> tuple[str, str]:
        token = self._peek()
        if token is None:
            raise _Unparsable("end of expression")
        self._at += 1
        return token

    def _accept(self, kind: str, value: str | None = None) -> bool:
        token = self._peek()
        if (
            token is None
            or token[0] != kind
            or (value is not None and token[1] != value)
        ):
            return False
        self._at += 1
        return True

    def parse(self):
        node = self.expr()
        if self._peek() is not None:
            raise _Unparsable(str(self._peek()))
        return node

    def expr(self):
        node = self.term()
        while self._accept("keyword", "OR"):
            node = ("or", node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self._accept("keyword", "AND"):
            node = ("and", node, self.factor())
        return node

    def factor(self):
        if self._accept("keyword", "NOT"):
            return ("not", self.factor())
        if self._accept("lparen"):
            node = self.expr()
            if not self._accept("rparen"):
                raise _Unparsable("expected )")
            return node
        return self.predicate()

    def operand(self):
        kind, value = self._take()
        if kind == "name":
            return ("col", value)
        if kind == "number":
            return ("lit", float(value) if "." in value else int(value))
        if kind == "string":
            return ("lit", value[1:-1].replace("''", "'"))
        if kind == "keyword" and value in ("TRUE", "FALSE"):
            return ("lit", value == "TRUE")
        if kind == "keyword" and value == "NULL":
            return ("lit", None)
        raise _Unparsable(f"{kind} {value}")

    def predicate(self):
        left = self.operand()
        if self._accept("keyword", "IS"):
            negated = self._accept("keyword", "NOT")
            if not self._accept("keyword", "NULL"):
                raise _Unparsable("expected NULL")
            return ("isnull", left, negated)
        negated = self._accept("keyword", "NOT")
        if self._accept("keyword", "IN"):
            if not self._accept("lparen"):
                raise _Unparsable("expected (")
            items = [self.operand()]
            while self._accept("comma"):
                items.append(self.operand())
            if not self._accept("rparen"):
                raise _Unparsable("expected )")
            return ("in", left, items, negated)
        if negated:
            raise _Unparsable("NOT without IN")
        kind, value = self._take()
        if kind != "cmp":
            raise _Unparsable(f"expected comparison, got {value}")
        return ("cmp", value, left, self.operand())


_COMPARISONS: dict[str, typing.Callable[[typing.Any, typing.Any], bool]] = {
    "=": lambda a, b: a == b,
    "<>": lambda a, b: a != b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _value(node, row: dict) -> typing.Any:
    kind, payload = node
    if kind == "lit":
        return payload
    if payload not in row:
        raise _Unparsable(f"column {payload}")
    return row[payload]


def _evaluate(node, row: dict) -> bool | None:
    kind = node[0]
    if kind == "and":
        left, right = _evaluate(node[1], row), _evaluate(node[2], row)
        if left is False or right is False:
            return False
        return None if left is None or right is None else True
    if kind == "or":
        left, right = _evaluate(node[1], row), _evaluate(node[2], row)
        if left is True or right is True:
            return True
        return None if left is None or right is None else False
    if kind == "not":
        inner = _evaluate(node[1], row)
        return None if inner is None else not inner
    if kind == "isnull":
        is_null = _value(node[1], row) is None
        return (not is_null) if node[2] else is_null
    if kind == "in":
        left = _value(node[1], row)
        if left is None:
            return None
        values = [_value(item, row) for item in node[2]]
        found = left in values
        if not found and any(v is None for v in values):
            return None
        return (not found) if node[3] else found
    left, right = _value(node[2], row), _value(node[3], row)
    if left is None or right is None:
        return None
    try:
        return _COMPARISONS[node[1]](left, right)
    except TypeError as error:
        raise _Unparsable(str(error)) from None


def violates_check(definition: str, row: dict) -> bool:
    """Whether PostgreSQL would refuse `row` for this CHECK.

    False whenever that cannot be established -- an expression outside the
    grammar, a column the row does not carry, or a comparison that is NULL
    and therefore unknown -- so this never refuses what the database accepts.
    """
    body = definition.strip()
    if not body.upper().startswith("CHECK"):
        return False
    body = body[len("CHECK") :].strip()
    try:
        node = _Parser(_tokenize(body)).parse()
        return _evaluate(node, row) is False
    except _Unparsable, RecursionError, ValueError:
        return False
