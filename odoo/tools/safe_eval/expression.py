"""Evaluate simple expressions with a restricted Python syntax.

Prefer this utility over `safe_eval` when only basic arithmetic,
comparisons, boolean logic, variables, and simple dict/list/tuple
access are needed.
"""
import ast
from types import NoneType
from typing import Any

from odoo.tools.lru import LRU
from odoo.tools.misc import OrderedSet

from . import unsafe_eval

MAX_INT_POW_EXP = 1024


def _safe_pow(a, b):
    if isinstance(a, int) and isinstance(b, int) and b > MAX_INT_POW_EXP:
        raise ValueError("Exponent too large")
    res = pow(a, b)
    if isinstance(res, complex):
        raise TypeError(f"Complex numbers are not supported ({a!r} ** {b!r})")
    return res


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

_EXPR_EVAL_CACHE = LRU(1000)

# whitelisted nodes, no need to visit children
_AST_OK = frozenset(c.__name__ for c in (
    # Only loading is allowed
    ast.Load,
    # BOOL_OP
    ast.And, ast.Or,
    # BIN_OP
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
    # UNARY_OP
    ast.Not, ast.UAdd, ast.USub,
    # COMPARE_OP
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
    ast.Is, ast.IsNot
))
# whitelisted nodes, visit all children
_AST_GENERIC = frozenset(c.__name__ for c in (
    ast.Dict, ast.Subscript, ast.List, ast.Tuple, ast.Slice,
    ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.IfExp,
))


def eval_name(context, name):
    # ast.Name accessor
    try:
        return context[name]
    except KeyError:
        raise NameError(name) from None


def eval_attr(obj, name):
    # ast.Attribute accessor
    from odoo.models import BaseModel  # noqa: PLC0415
    if isinstance(obj, BaseModel):
        if field := obj._fields.get(name):
            return field.__get__(obj)
        if name == 'ids':
            return obj.ids
        if name == '_name':
            return obj._name
    raise AttributeError(
        f"Attribute access is only supported on Odoo recordsets, got {type(obj).__name__!r}"
    )


class _ExprMakeLambda(ast.NodeTransformer):
    """ Transform an expression into a lambda function. """
    def __init__(self):
        self._name_whitelist = set()

    def visit_Expression(self, node):
        """ expr => lambda ctx: visited_expr """
        body = self.visit(node.body)
        args = ast.arguments(posonlyargs=[ast.arg('ctx')], args=[], vararg=None, defaults=[], kw_defaults=[], kwarg=None, kwonlyargs=[])
        body_lambda = ast.Lambda(args, body=ast.Pass())
        ast.fix_missing_locations(body_lambda)
        body_lambda.body = body  # move current body into the lambda content
        node.body = body_lambda  # return the lambda
        return node

    def visit_BinOp(self, node):
        """ Generic visit, except for `_pow(a, b)`."""
        node = super().generic_visit(node)
        if isinstance(node.op, ast.Pow):
            load = ast.Load()
            func = ast.Name('_pow', load)
            call = ast.Call(func, [node.left, node.right], [])
            ast.copy_location(load, node)
            ast.copy_location(func, node)
            ast.copy_location(call, node)
            return call
        return node

    def visit_Dict(self, node):
        if not all(key is not None for key in node.keys):
            raise SyntaxError("Dict unpacking is not supported")
        return super().generic_visit(node)

    def visit_Set(self, node):
        """ {x...} => set([x...])

        This allows to use custom set implementation. """
        load = ast.Load()
        func = ast.Name('set', load)
        arg = ast.List([self.visit(e) for e in node.elts], load)
        call = ast.Call(func, [arg], [])
        ast.copy_location(load, node)
        ast.copy_location(func, node)
        ast.copy_location(arg, node)
        ast.copy_location(call, node)
        return call

    def visit_Call(self, node):
        if node.keywords:
            raise SyntaxError("Keyword arguments are not supported in function calls")
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
            raise NameError("Only %s function calls are allowed" % ", ".join(_ALLOWED_CALLS))
        self._name_whitelist.add(node.func)
        return super().generic_visit(node)

    def visit_Constant(self, node):
        value = node.value
        if isinstance(value, (NoneType, bytes, str, int, float, bool)):
            return node
        raise TypeError(f"Unsupported constant: {type(value).__name__}")

    def visit_Attribute(self, node):
        """ a.b => _ATTR(a, 'b') """
        load = self.visit(node.ctx)
        func = ast.Name('_ATTR', load)
        value = self.visit(node.value)
        attr = ast.Constant(node.attr)
        call = ast.Call(func, [value, attr], [])
        ast.copy_location(func, node)
        ast.copy_location(attr, node)
        ast.copy_location(call, node)
        return call

    def visit_Name(self, node):
        """ a => _NAME(ctx, 'a')

        Either name is in `ctx` or it was validated as a name of Call.
        """
        if node in self._name_whitelist:  # whitelisted for function calls
            return node
        load = self.visit(node.ctx)
        func = ast.Name('_NAME', load)
        ctx = ast.Name('ctx', load)
        name = ast.Constant(node.id)
        call = ast.Call(func, [ctx, name], [])
        call = ast.fix_missing_locations(call)
        return call

    def generic_visit(self, node):
        name = node.__class__.__name__
        if name in _AST_OK:
            return node
        if name in _AST_GENERIC:
            return super().generic_visit(node)
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
    compiled_func = _EXPR_EVAL_CACHE.get(expr)
    if compiled_func is None:
        node = ast.parse(expr, mode="eval")
        node_lambda = _ExprMakeLambda().visit(node)
        compiled = compile(node_lambda, '<expr_eval>', 'eval')
        compiled_func = unsafe_eval(compiled, dict(
            _ALLOWED_CALLS,
            __builtins__={},
            _ATTR=eval_attr,
            _NAME=eval_name,
            _pow=_safe_pow,
        ))
        if len(expr) < 200:
            _EXPR_EVAL_CACHE[expr] = compiled_func
    return compiled_func(context or {})
