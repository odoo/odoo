from collections.abc import Iterable
from typing import Final

STANDARD_CONDITION_OPERATORS: Final[frozenset[str]] = frozenset(
    [
        "any",
        "not any",
        "any!",
        "not any!",
        "in",
        "not in",
        "<",
        ">",
        "<=",
        ">=",
        "like",
        "not like",
        "ilike",
        "not ilike",
        "=like",
        "not =like",
        "=ilike",
        "not =ilike",
        "=~",
        "not =~",
    ]
)

EXTENDED_CONDITION_OPERATORS: Final[frozenset[str]] = frozenset(
    ("=?", "<>", "==", "=", "!=", "parent_of", "child_of")
)

CONDITION_OPERATORS: Final[frozenset[str]] = (
    STANDARD_CONDITION_OPERATORS | EXTENDED_CONDITION_OPERATORS
)

ACCEPTED_CONDITION_OPERATORS: set[str] = set(CONDITION_OPERATORS)


def register_condition_operators(operators: Iterable[str]) -> frozenset[str]:
    operators = frozenset(operators)
    if not operators:
        raise ValueError("Missing operator to register")
    if collisions := operators & CONDITION_OPERATORS:
        raise ValueError(
            f"cannot redefine the framework's own operator(s) "
            f"{sorted(collisions)!r}; addon operators must be new names."
        )
    if malformed := {op for op in operators if not op or op != op.lower()}:
        raise ValueError(
            f"domain operator(s) {sorted(malformed)!r} must be non-empty and "
            f"lower-case; DomainCondition.normalize() lower-cases the operator "
            f"before looking it up, so a mixed-case name could never match."
        )
    ACCEPTED_CONDITION_OPERATORS.update(operators)
    return operators


LIKE_CONDITION_OPERATORS: Final[frozenset[str]] = frozenset(
    op for op in STANDARD_CONDITION_OPERATORS if op.endswith("like")
)

# a POSIX regular expression the column must match (`~`), like `=like`
# without wildcard wrapping and without unaccent
REGEX_CONDITION_OPERATORS: Final[frozenset[str]] = frozenset(("=~", "not =~"))

INTERNAL_CONDITION_OPERATORS: Final[frozenset[str]] = frozenset(("any!", "not any!"))

SUBDOMAIN_OPERATORS: Final[frozenset[str]] = frozenset(
    ("any", "any!", "not any", "not any!")
)

SUBDOMAIN_OR_IN_OPERATORS: Final[frozenset[str]] = SUBDOMAIN_OPERATORS | frozenset(
    ("in", "not in")
)

NEGATIVE_CONDITION_OPERATORS: Final[dict[str, str]] = {
    "not any": "any",
    "not any!": "any!",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
    "not =like": "=like",
    "not =ilike": "=ilike",
    "not =~": "=~",
    "!=": "=",
    "<>": "=",
}

INVERSE_OPERATOR: Final[dict[str, str]] = {
    **NEGATIVE_CONDITION_OPERATORS,
    **{
        positive: negative
        for negative, positive in NEGATIVE_CONDITION_OPERATORS.items()
        if negative != "<>"
    },
}

INVERSE_INEQUALITY: Final[dict[str, str]] = {
    "<": ">=",
    ">": "<=",
    ">=": "<",
    "<=": ">",
}

TRUE_LEAF: Final[tuple[int, str, int]] = (1, "=", 1)
FALSE_LEAF: Final[tuple[int, str, int]] = (0, "=", 1)

__all__ = [
    "CONDITION_OPERATORS",
    "EXTENDED_CONDITION_OPERATORS",
    "FALSE_LEAF",
    "INTERNAL_CONDITION_OPERATORS",
    "INVERSE_INEQUALITY",
    "INVERSE_OPERATOR",
    "LIKE_CONDITION_OPERATORS",
    "NEGATIVE_CONDITION_OPERATORS",
    "REGEX_CONDITION_OPERATORS",
    "STANDARD_CONDITION_OPERATORS",
    "SUBDOMAIN_OPERATORS",
    "SUBDOMAIN_OR_IN_OPERATORS",
    "TRUE_LEAF",
]
