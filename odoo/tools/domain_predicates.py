import operator

# The in-memory predicate each domain operator stands for, for a `search=`
# method that answers by filtering records in Python.
#
# `=` and `!=` are absent deliberately: the domain optimiser rewrites them to
# `in` and `not in` before a field's search method is called, so a branch for
# either is unreachable. A search method is handed these six and no others,
# and its `value` arrives as a FrozenOrderedSet for the two set operators.
# The two that take a container rather than a scalar; their value arrives as a
# FrozenOrderedSet, so a caller coercing the value must skip them.
SET_DOMAIN_OPERATORS = frozenset({"in", "not in"})

DOMAIN_PREDICATES = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "in": lambda element, container: element in container,
    "not in": lambda element, container: element not in container,
}
