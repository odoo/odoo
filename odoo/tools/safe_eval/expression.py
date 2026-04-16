"""Evaluate simple expressions with a restricted Python syntax.

Prefer this utility over `safe_eval` when only basic arithmetic,
comparisons, boolean logic, variables, and simple dict/list/tuple
access are needed.
"""
import ast
import operator
from types import NoneType
from typing import Any

from odoo.tools.misc import OrderedSet

MAX_INT_POW_EXP = 1024


def _safe_pow(a, b):
    if isinstance(a, int) and isinstance(b, int) and b > MAX_INT_POW_EXP:
        raise ValueError("Exponent too large")
    res = pow(a, b)
    if isinstance(res, complex):
        raise TypeError(f"Complex numbers are not supported ({a!r} ** {b!r})")
    return res


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: _safe_pow,
    ast.FloorDiv: operator.floordiv,
}

_UNARY_OPS = {
    ast.Not: operator.not_,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda element, container: element in container,
    ast.NotIn: lambda element, container: element not in container,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
}

_ALLOWED_CALLS = {
    # funcs
    'max': max,
    'min': min,
    'round': round,
    # types
    'float': float,
    'int': int,
    'set': OrderedSet,
}


_BOOL_OP_SHORT_CIRCUIT_TEST = {
    ast.And: operator.not_,
    ast.Or: operator.truth,
}


def _get_func(ops_set, node):
    try:
        return ops_set[type(node)]
    except KeyError:
        raise SyntaxError(f"Unsupported operator: {type(node).__name__}") from None


class _ExprEval(ast.NodeVisitor):
    """Evaluate supported expressions for `expr_eval`."""
    __slots__ = ("context",)

    def __init__(self, context: dict[str, Any]):
        self.context = context

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_BoolOp(self, node):
        test = _get_func(_BOOL_OP_SHORT_CIRCUIT_TEST, node.op)
        for value in node.values:
            result = self.visit(value)
            if test(result):
                return result
        return result

    def visit_BinOp(self, node):
        op = _get_func(_BIN_OPS, node.op)
        return op(self.visit(node.left), self.visit(node.right))

    def visit_UnaryOp(self, node):
        op = _get_func(_UNARY_OPS, node.op)
        return op(self.visit(node.operand))

    def visit_Dict(self, node):
        out = {}
        for key_node, value_node in zip(node.keys, node.values):
            if key_node is None:
                raise SyntaxError("Dict unpacking is not supported")
            out[self.visit(key_node)] = self.visit(value_node)
        return out

    def visit_Set(self, node):
        return OrderedSet(self.visit(item) for item in node.elts)

    def visit_Compare(self, node):
        current = self.visit(node.left)
        for op_node, right_node in zip(node.ops, node.comparators):
            op = _get_func(_COMPARE_OPS, op_node)
            next_value = self.visit(right_node)
            if not op(current, next_value):
                return False
            current = next_value
        return True

    def visit_Call(self, node):
        if node.keywords:
            raise SyntaxError("Keyword arguments are not supported in function calls")
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
            raise NameError("Only %s function calls are allowed" % ", ".join(_ALLOWED_CALLS))

        func = _ALLOWED_CALLS[node.func.id]
        return func(*(self.visit(arg) for arg in node.args))

    def visit_Constant(self, node):
        value = node.value
        if isinstance(value, (NoneType, bytes, str, int, float, bool)):
            return value
        raise TypeError(f"Unsupported constant: {type(value).__name__}")

    def visit_IfExp(self, node):
        return self.visit(node.body) if self.visit(node.test) else self.visit(node.orelse)

    def visit_Subscript(self, node):
        return self.visit(node.value)[self.visit(node.slice)]

    def visit_Name(self, node):
        try:
            return self.context[node.id]
        except KeyError as error:
            raise NameError(node.id) from error

    def visit_List(self, node):
        return [self.visit(item) for item in node.elts]

    def visit_Tuple(self, node):
        return tuple(self.visit(item) for item in node.elts)

    def visit_Slice(self, node):
        return slice(
            self.visit(node.lower) if node.lower is not None else None,
            self.visit(node.upper) if node.upper is not None else None,
            self.visit(node.step) if node.step is not None else None,
        )

    def generic_visit(self, node):
        raise SyntaxError(f"Unsupported syntax: {type(node).__name__}")


def expr_eval(expr: str, context: dict[str, Any] | None = None) -> Any:
    """Evaluate a restricted Python-like expression.

    Supported syntax includes literals, variables from ``context``,
    list/tuple/set/dict literals, indexing, slicing, arithmetic,
    boolean operations, comparisons, and a calls to min() and max().

    Example::

        expr_eval("amount * 2", {"amount": 21})
        expr_eval("[('user_id', '=', user_id)]", {"user_id": 7})

    :param expr: Expression to evaluate.
    :param context: Variables available by name in the expression.
    :returns: The evaluated result.
    :raises SyntaxError: expression is empty or uses unsupported syntax
    :raises NameError: expression uses an unknown variable/function name
    :raises TypeError: expression uses an unsupported constant type
    """
    assert type(expr) is str, "Expression must be a string"
    if not (expr := expr.strip()):
        raise SyntaxError("Expression cannot be empty")
    return _ExprEval(context or {}).visit(ast.parse(expr, mode="eval"))
