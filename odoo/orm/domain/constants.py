"""Domain operator constants and mappings.

This module contains all the operator constants used in domain expressions:
- STANDARD_CONDITION_OPERATORS: Standard operators supported at all levels
- CONDITION_OPERATORS: All available operators (modifiable for optimizations)
- NEGATIVE_CONDITION_OPERATORS: Operators with negative semantics
- Internal operator mappings for negation and inversion
"""

STANDARD_CONDITION_OPERATORS = frozenset(
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
    ]
)
"""List of standard operators for conditions.
This should be supported in the framework at all levels.

- `any` works for relational fields and `id` to check if a record matches
  the condition
  - if value is SQL or Query, see `any!`
  - if bypass_search_access is set on the field, see `any!`
  - if value is a Domain for a many2one (or `id`),
    _search with active_test=False
  - if value is a Domain for a x2many,
    _search on the comodel of the field (with its context)
- `any!` works like `any` but bypass adding record rules on the comodel
- `in` for equality checks where the given value is a collection of values
  - the collection is transformed into OrderedSet
  - False value indicates that the value is *not set*
  - for relational fields
    - if int, bypass record rules
    - if str, search using display_name of the model
  - the value should have the type of the field
  - SQL type is always accepted
- `<`, `>`, ... inequality checks, similar behaviour to `in` with a single value
- string pattern comparison
  - `=like` case-sensitive compare to a string using SQL like semantics
  - `=ilike` case-insensitive with `unaccent` comparison to a string
  - `like`, `ilike` behave like the preceding methods, but add a wildcards
    around the value
"""

CONDITION_OPERATORS = set(
    STANDARD_CONDITION_OPERATORS
)  # modifiable (for optimizations only)
"""
List of available operators for conditions.
The non-standard operators can be reduced to standard operators by using the
optimization function. See the respective optimization functions for the
details.
"""

INTERNAL_CONDITION_OPERATORS = frozenset(("any!", "not any!"))

SUBDOMAIN_OPERATORS = frozenset(("any", "any!", "not any", "not any!"))
"""Operators whose value must be parsed as a Domain when ``internal=True``.

Referenced by ``Domain.__new__`` in both the single-condition fast path
and the stack-based parser.  Keeping this as a named constant prevents
the two code paths from diverging."""

NEGATIVE_CONDITION_OPERATORS = {
    "not any": "any",
    "not any!": "any!",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
    "not =like": "=like",
    "not =ilike": "=ilike",
    "!=": "=",
    "<>": "=",
}
"""A subset of operators with a 'negative' semantic, mapping to the 'positive' operator."""

# negations for operators (used in DomainNot)
INVERSE_OPERATOR = {
    # from NEGATIVE_CONDITION_OPERATORS
    "not any": "any",
    "not any!": "any!",
    "not in": "in",
    "not like": "like",
    "not ilike": "ilike",
    "not =like": "=like",
    "not =ilike": "=ilike",
    "!=": "=",
    "<>": "=",
    # positive to negative
    "any": "not any",
    "any!": "not any!",
    "in": "not in",
    "like": "not like",
    "ilike": "not ilike",
    "=like": "not =like",
    "=ilike": "not =ilike",
    "=": "!=",
}
"""Dict to find the inverses of the operators."""

INVERSE_INEQUALITY = {
    "<": ">=",
    ">": "<=",
    ">=": "<",
    "<=": ">",
}
"""Dict to find the inverse of inequality operators.
Handled differently because of null values."""

TRUE_LEAF = (1, "=", 1)
FALSE_LEAF = (0, "=", 1)

__all__ = [
    "CONDITION_OPERATORS",
    "FALSE_LEAF",
    "INTERNAL_CONDITION_OPERATORS",
    "INVERSE_INEQUALITY",
    "INVERSE_OPERATOR",
    "NEGATIVE_CONDITION_OPERATORS",
    "STANDARD_CONDITION_OPERATORS",
    "SUBDOMAIN_OPERATORS",
    "TRUE_LEAF",
]
