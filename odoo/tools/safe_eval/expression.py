"""Evaluate simple expressions with a restricted Python syntax.

Prefer this utility over `safe_eval` when only basic arithmetic,
comparisons, boolean logic, variables, and simple dict/list/tuple
access are needed.
"""
import ast
import functools
import operator
import threading
from collections.abc import Callable
from types import NoneType
from typing import Any

from odoo.tools.misc import OrderedSet

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
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
    'min': min,
    'max': max,
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
    """Evaluate the supported AST nodes for `expr_eval` into an executable function."""

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_BoolOp(self, node):
        values = tuple(self.visit(value) for value in node.values)
        test = _get_func(_BOOL_OP_SHORT_CIRCUIT_TEST, node.op)

        def evaluate(context):
            for value in values:
                result = value(context)
                if test(result):
                    break
            return result

        return evaluate

    def visit_BinOp(self, node):
        op = _get_func(_BIN_OPS, node.op)
        left = self.visit(node.left)
        right = self.visit(node.right)
        return lambda context: op(left(context), right(context))

    def visit_UnaryOp(self, node):
        op = _get_func(_UNARY_OPS, node.op)
        operand = self.visit(node.operand)
        return lambda context: op(operand(context))

    def visit_Dict(self, node):
        keys = tuple(self.visit(key) for key in node.keys)
        values = tuple(self.visit(value) for value in node.values)

        def eval_dict(context):
            return {
                key(context): value(context)
                for key, value in zip(keys, values)
            }

        return eval_dict

    def visit_Set(self, node):
        items = tuple(self.visit(item) for item in node.elts)
        return lambda context: OrderedSet(item(context) for item in items)

    def visit_Compare(self, node):
        left = self.visit(node.left)
        ops = tuple(_get_func(_COMPARE_OPS, op_node) for op_node in node.ops)
        comparators = tuple(self.visit(right_node) for right_node in node.comparators)

        def eval_compare(context):
            current = left(context)

            for op, right in zip(ops, comparators):
                next_value = right(context)
                if not op(current, next_value):
                    return False
                current = next_value

            return True

        return eval_compare

    def visit_Call(self, node):
        if node.keywords:
            raise SyntaxError("Keyword arguments are not supported in function calls")
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
            raise NameError("Only %s function calls are allowed" % ", ".join(_ALLOWED_CALLS.keys()))

        func = _ALLOWED_CALLS[node.func.id]
        args = tuple(self.visit(arg) for arg in node.args)

        def eval_call(context):
            return func(*(arg(context) for arg in args))

        return eval_call

    def visit_Constant(self, node):
        value = node.value
        if isinstance(value, (NoneType, bytes, str, int, float, bool)):
            return lambda context: value
        raise TypeError(f"Unsupported constant: {type(value).__name__}")

    def visit_IfExp(self, node):
        test = self.visit(node.test)
        body = self.visit(node.body)
        orelse = self.visit(node.orelse)

        return lambda context: body(context) if test(context) else orelse(context)

    def visit_Subscript(self, node):
        value = self.visit(node.value)
        slice_ = self.visit(node.slice)

        return lambda context: value(context)[slice_(context)]

    def visit_Name(self, node):
        name = node.id

        def eval_name(context):
            try:
                return context[name]
            except KeyError as error:
                raise NameError(name) from error

        return eval_name

    def visit_List(self, node):
        items = tuple(self.visit(item) for item in node.elts)
        return lambda context: [item(context) for item in items]

    def visit_Tuple(self, node):
        items = tuple(self.visit(item) for item in node.elts)
        return lambda context: tuple(item(context) for item in items)

    def visit_Slice(self, node):
        lower = self.visit(node.lower) if node.lower is not None else None
        upper = self.visit(node.upper) if node.upper is not None else None
        step = self.visit(node.step) if node.step is not None else None

        return lambda context: slice(
            lower(context) if lower is not None else None,
            upper(context) if upper is not None else None,
            step(context) if step is not None else None,
        )

    def generic_visit(self, node):
        raise SyntaxError(f"Unsupported syntax: {type(node).__name__}")


_expr_eval = _ExprEval()


def _compile_expr_eval_func(expr: str) -> Callable[[dict[str, Any]], Any]:
    return _expr_eval.visit(ast.parse(expr, mode="eval"))


@functools.cache
def _get_db_expr_compiler(dbname: str) -> Callable[[str], Callable[[dict[str, Any]], Any]]:
    # Scope the cache per DB: workers are shared, and a global cache leaks whether
    # another DB recently evaluated the same expression.
    return functools.lru_cache(maxsize=2048)(_compile_expr_eval_func)


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
    # cache per db to avoid leaking an oracle to read info across dbs
    db_compiler = _get_db_expr_compiler(getattr(threading.current_thread(), 'dbname', ''))
    compiled_func = db_compiler(expr)
    return compiled_func(context or {})
