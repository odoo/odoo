"""Domain expression processing package.

The domain represents a first-order logical expression.
The main duty of this package is to represent filter conditions on models
and ease rewriting them.

The `Domain` is represented as an AST which is a predicate using boolean
operators.
- n-ary operators: AND, OR
- unary operator: NOT
- boolean constants: TRUE, FALSE
- (simple) conditions: (expression, operator, value)

Conditions are triplets of `(expression, operator, value)`.
`expression` is usually a field name. It can be an expression that uses the
dot-notation to traverse relationships or accesses properties of the field.
The traversal of relationships is equivalent to using the `any` operator.
`operator` in one of the CONDITION_OPERATORS, the detailed description of what
is possible is documented there.
`value` is a Python value which should be supported by the operator.

Package Structure:
- constants.py: Operator constants and mappings
- ast.py: Domain AST classes (Domain, DomainCondition, etc.)
- optimizations.py: Domain optimization functions

Usage:
    from odoo.orm.domain import Domain, CONDITION_OPERATORS

    # Create a domain
    domain = Domain([('name', '=', 'test')])

    # Combine domains
    combined = Domain('a', '=', 1) & Domain('b', '=', 2)

    # Use class methods
    Domain.AND([dom1, dom2, dom3])
    Domain.OR([dom1, dom2])
"""

# Import constants
from .constants import (
    STANDARD_CONDITION_OPERATORS,
    CONDITION_OPERATORS,
    INTERNAL_CONDITION_OPERATORS,
    NEGATIVE_CONDITION_OPERATORS,
    INVERSE_OPERATOR,
    INVERSE_INEQUALITY,
    TRUE_LEAF,
    FALSE_LEAF,
)

# Import AST classes
from .ast import (
    # Optimization infrastructure
    OptimizationLevel,
    MAX_OPTIMIZE_ITERATIONS,
    ANY_TYPES,
    # Domain classes
    Domain,
    DomainBool,
    DomainNot,
    DomainNary,
    DomainAnd,
    DomainOr,
    DomainCustom,
    DomainCondition,
)

# Import and register optimizations (MUST be after AST imports)
# This ensures all optimization functions are registered
from . import optimizations

# Re-export optimization decorators for extending
from .optimizations import (
    operator_optimization,
    field_type_optimization,
    nary_optimization,
    nary_condition_optimization,
)

__all__ = [
    "ANY_TYPES",
    "CONDITION_OPERATORS",
    "FALSE_LEAF",
    "INTERNAL_CONDITION_OPERATORS",
    "INVERSE_INEQUALITY",
    "INVERSE_OPERATOR",
    "MAX_OPTIMIZE_ITERATIONS",
    "NEGATIVE_CONDITION_OPERATORS",
    # Constants
    "STANDARD_CONDITION_OPERATORS",
    "TRUE_LEAF",
    # Domain classes
    "Domain",
    "DomainAnd",
    "DomainBool",
    "DomainCondition",
    "DomainCustom",
    "DomainNary",
    "DomainNot",
    "DomainOr",
    # Optimization infrastructure
    "OptimizationLevel",
    "field_type_optimization",
    "nary_condition_optimization",
    "nary_optimization",
    "operator_optimization",
]
