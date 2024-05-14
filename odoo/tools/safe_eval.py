# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
safe_eval module - methods intended to provide more restricted alternatives to
                   evaluate simple and/or untrusted code.

Methods in this module are typically used as alternatives to eval() to parse
OpenERP domain strings, conditions and expressions, mostly based on locals
condition/math builtins.
"""

from __future__ import annotations

import ast
import math
import datetime
import logging
import odoo
import odoo.exceptions
import werkzeug.exceptions

from dateutil.relativedelta import relativedelta
from email.message import EmailMessage
from enum import EnumMeta
from functools import reduce, partial
from odoo.tools.json import JSON
from psycopg2 import OperationalError
from types import (
    BuiltinFunctionType,
    BuiltinMethodType,
    FunctionType,
    GeneratorType,
    LambdaType,
    MethodDescriptorType,
    MethodType,
    ModuleType,
)
from typing import Any, Optional, Literal, Type, Callable, cast, TypeVar
from unittest.mock import Mock, MagicMock

unsafe_eval = eval
_logger = logging.getLogger(__name__)

# --- Type Hints --------------------------------------------------------------

T = TypeVar("T")
OptionalTuple = tuple[()] | tuple[T, ...]
ContextType = dict[str, Any]

_BUILTINS: ContextType = {
    "True": True,
    "False": False,
    "None": None,
    "bytes": bytes,
    "str": str,
    "unicode": str,
    "bool": bool,
    "int": int,
    "float": float,
    "enumerate": enumerate,
    "dict": dict,
    "list": list,
    "tuple": tuple,
    "map": map,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "reduce": reduce,
    "filter": filter,
    "sorted": sorted,
    "round": round,
    "len": len,
    "repr": repr,
    "set": set,
    "all": all,
    "any": any,
    "ord": ord,
    "chr": chr,
    "divmod": divmod,
    "isinstance": isinstance,
    "range": range,
    "xrange": range,
    "zip": zip,
    "Exception": Exception,
    "hasattr": hasattr,
    "floor": math.floor,
    "ceil": math.ceil,
}

_CALLABLE_TYPES: frozenset[type] = frozenset(
    {
        BuiltinFunctionType,  # print, len, ...
        BuiltinMethodType,  # [].append, int.from_bytes, ...
        FunctionType,  # lambda, def, ...
        MethodType,  # foo.bar(), ...
        MethodDescriptorType,  # str.join(), ...
        LambdaType,  # lambda, ...
        GeneratorType,  # (x for x in range(10)), ...
        partial,  # partial functions
    }
)

_ALLOWED_TYPES: frozenset[Type] = frozenset(
    {
        JSON,
        bool,
        bytes,
        complex,
        datetime.date,
        datetime.datetime,
        datetime.time,
        datetime.timedelta,
        dict,
        enumerate,
        float,
        int,
        list,
        odoo.exceptions.UserError,
        range,
        relativedelta,
        reversed,
        set,
        slice,
        str,
        tuple,
        zip,
    }
)

_wrapped_types: tuple[type, ...] = (
    Exception,
    filter,
    map,
)

_ALLOWED_INSTANCES: frozenset[Type] = frozenset(
    {
        EmailMessage,
        EnumMeta,
        GeneratorType,
        odoo.api.Environment,
        odoo.models.BaseModel,
        odoo.models.NewId,
        odoo.sql_db.Cursor,
        odoo.sql_db.TestCursor,
        type({}.items()),  # <class 'dict_items'>
        type({}.keys()),  # <class 'dict_keys'>
        type({}.values()),  # <class 'dict_values'>
        type(None),  # <class 'NoneType'>
    }
    | _ALLOWED_TYPES
)

_wrapped_instances: tuple[type, ...] = (
    (
        Mock,
        MagicMock,
    )
    + _wrapped_types
    + tuple(_CALLABLE_TYPES)
)

# Roots node, they are required in all cases
_AST_BASE_NODES: frozenset[Type[ast.AST]] = frozenset(
    {
        ast.Expr,
        ast.Expression,
        ast.Module,
    }
)

_AST_MATH_NODES: frozenset[Type[ast.AST]] = frozenset(
    {
        ast.Constant,  # 1, 2, 3, ...
        ast.Add,  # +
        ast.And,  # and
        ast.BinOp,  # x + y
        ast.BitAnd,  # &
        ast.BitOr,  # |
        ast.BitXor,  # ^
        ast.BoolOp,  # x and y
        ast.Div,  # /
        ast.Eq,  # ==
        ast.FloorDiv,  # //
        ast.Gt,  # >
        ast.GtE,  # >=
        ast.In,  # in
        ast.Invert,  # ~
        ast.Is,  # is
        ast.IsNot,  # is not
        ast.LShift,  # <<
        ast.Lt,  # <
        ast.LtE,  # <=
        ast.Mod,  # %
        ast.Mult,  # *
        ast.Not,  # not
        ast.NotEq,  # !=
        ast.NotIn,  # not in
        ast.Or,  # or
        ast.Pow,  # **
        ast.RShift,  # >>
        ast.Sub,  # -
        ast.UAdd,  # +x
        ast.UnaryOp,  # -x
        ast.USub,  # -x
    }
    | _AST_BASE_NODES
)

_AST_ALLOWED_NODES: frozenset[Type[ast.AST]] = frozenset(
    {
        ast.Load,
        ast.Store,
        ast.arg,  # def foo(x): ... (x is an arg)
        ast.arguments,  # def foo(x): ... ([x] is an arguments, it's a list of args)
        ast.Assign,  # x = 1
        ast.Attribute,  # x.y
        ast.AugAssign,  # +=
        ast.Break,  # break
        ast.Call,  # x()
        ast.Compare,  # x < y
        ast.comprehension,  # for x in range(10) (in list comprehension for example)
        ast.Continue,  # continue
        ast.Dict,  # { x: x }
        ast.DictComp,  # { x: x for x in range(10) }
        ast.ExceptHandler,  # try: ... except Exception as e: ...
        ast.For,  # for x in range(10): ...
        ast.FormattedValue,  # f"{x}"
        ast.FunctionDef,  # def foo(): ...
        ast.GeneratorExp,  # (x for x in range(10))
        ast.If,  # if x: ...
        ast.IfExp,  # x if x else y
        ast.JoinedStr,  # f"{'x'}"
        ast.keyword,  # foo(x=1) (x=1 is a keyword)
        ast.Lambda,  # lambda x: x
        ast.List,  # [1, 2, 3]
        ast.ListComp,  # [x for x in range(10)]
        ast.Name,  # x
        ast.Pass,  # pass
        ast.Raise,  # raise Exception()
        ast.Return,  # return x
        ast.Set,  # {1, 2, 3}
        ast.SetComp,  # {x for x in range(10)}
        ast.Slice,  # x[1:2]
        ast.Subscript,  # x[1]
        ast.Starred,  # *args
        ast.Try,  # try: ...
        ast.Tuple,  # (1, 2, 3)
        ast.While,  # while x: ...
    }
    | _AST_MATH_NODES
)

_ALLOWED_MODULES: frozenset[str] = frozenset(
    {
        "datetime",
        "dateutil",
        "json",
        "pytz",
        "time",
        *[f"dateutil.{mod}" for mod in ["parser", "relativedelta", "rrule", "tz"]],
    }
)


# --- Utils -------------------------------------------------------------------


def _check_attribute_name(name: str) -> None:
    if "__" in name:
        raise NameError(f"unsafe node: {name} (dunder name)")


def call_wrapper(node: ast.AST) -> ast.Call:
    return ast.Call(
        func=ast.Name("__SafeWrapper", ctx=ast.Load()),
        args=[],
        keywords=[
            ast.keyword(
                arg="__obj",
                value=ast.Call(
                    func=ast.Name("__type_checker", ctx=ast.Load()),
                    args=[],
                    keywords=[
                        ast.keyword(arg="__obj", value=node),
                    ],
                ),
            ),
            ast.keyword(
                arg="__type_checker", value=ast.Name("__type_checker", ctx=ast.Load())
            ),
        ],
    )


# --- Environment -------------------------------------------------------------


class SafeWrapper:
    __slots__ = ("__obj", "__type_checker")

    def __init__(self, **kwargs):
        self.__obj = kwargs.pop("__obj")
        self.__type_checker = kwargs.pop("__type_checker")

    def __getattr__(self, name: str) -> Any:
        _check_attribute_name(name)
        if (
            isinstance(self.__obj, str)
            or (isinstance(self.__obj, type) and issubclass(self.__obj, str))
        ) and name in (
            "format",
            "format_map",
        ):
            raise ValueError(f"unsafe attribute access: {name} (string format)")

        return self.__type_checker(__obj=getattr(self.__obj, name))

    def __setattr__(self, name: str, value: Any):
        if "__" not in name:
            raise SyntaxError(f"unsafe attribute assignation: {name}")

        super().__setattr__(name, value)

    def __call__(self, *args, **kwargs) -> Any:
        for arg in (*args, *kwargs.values()):
            self.__type_checker(__obj=arg)

        return self.__type_checker(__obj=self.__obj(*args, **kwargs))

    def __repr__(self) -> str:
        return self.__obj.__repr__()

    def __getitem__(self, key: str) -> Any:
        key = self.__type_checker(__obj=key)
        return self.__type_checker(__obj=self.__obj[key])

    def __setitem__(self, key: str, value: Any) -> Any:
        key = self.__type_checker(__obj=key)
        value = self.__type_checker(__obj=value)
        self.__obj[key] = value

    def __iter__(self):
        for item in self.__obj:
            yield self.__type_checker(__obj=item)


def _prepare_environment(
    allowed_types: OptionalTuple[type] = (), allowed_instances: OptionalTuple[type] = ()
) -> dict[str, type | Callable[..., Any]]:
    allowed_type = allowed_types + tuple(_ALLOWED_TYPES)
    allowed_instance = (
        allowed_instances + tuple(_ALLOWED_INSTANCES) + allowed_type + (SafeWrapper,)
    )

    def type_checker(**kwargs) -> Any | SafeWrapper:
        obj = kwargs.pop("__obj")

        if obj is safe_eval or (
            callable(obj)
            and not isinstance(obj, SafeWrapper)
            and hasattr(obj, "__self__")
            and isinstance(obj.__self__, ModuleType)
            and obj.__self__.__name__ not in _ALLOWED_MODULES
            and obj not in _BUILTINS.values()):
            raise ValueError(f"unsafe object: {obj} (denied by black-list)")

        if isinstance(obj, allowed_instance) or (
            isinstance(obj, type) and issubclass(obj, allowed_type)
        ):
            return obj
        elif (
            isinstance(obj, _wrapped_instances)
            or (isinstance(obj, type) and issubclass(obj, _wrapped_types))
            or (isinstance(obj, ModuleType) and obj.__name__ in _ALLOWED_MODULES)
        ):
            return SafeWrapper(__obj=obj, __type_checker=type_checker)
        raise ValueError(f"unsafe object: {obj} (type not present in white-list)")

    def call_checker(**kwargs) -> Any:
        func = kwargs.pop("__func")
        f_args = kwargs.pop("__args")
        f_kwargs = kwargs.pop("__kwargs")

        type_checker(__obj=func)

        f_args = SafeWrapper(__obj=f_args, __type_checker=type_checker)

        f_kwargs = SafeWrapper(__obj=f_kwargs, __type_checker=type_checker)

        return type_checker(__obj=func(*f_args, **f_kwargs))

    return {
        "__type_checker": type_checker,
        "__call_checker": call_checker,
        "__SafeWrapper": SafeWrapper,
    }


# --- Ast Explorer ------------------------------------------------------------


class StoreChecker(ast.NodeTransformer):
    def __init__(self, stores: Optional[list] = None) -> None:
        self.stores = stores or []

    def visit_Name(self, node: ast.Name) -> ast.Call | ast.Name:
        if isinstance(node.ctx, ast.Load) and node.id in self.stores:
            return ast.Call(
                func=ast.Name("__type_checker", ctx=ast.Load()),
                args=[],
                keywords=[ast.keyword(arg="__obj", value=node)],
            )
        return node


class CodeChecker(ast.NodeTransformer):
    def __init__(
        self, ast_subset: frozenset[type[ast.AST]] | tuple[type[ast.AST], ...]
    ):
        self.ast_subset = ast_subset

    def visit(self, node: ast.AST) -> ast.AST:
        if not isinstance(node, tuple(self.ast_subset)):
            raise SyntaxError(  # noqa: TRY004 (Reason: It should be a syntax error, not a type error)
                f"unsafe node: {node.__class__.__name__} (node not allowed)"
            )

        visitor: Callable[[ast.AST], ast.AST] = getattr(
            self, f"explore_{node.__class__.__name__}", self.generic_visit
        )
        return visitor(node)

    def explore_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node = cast(ast.FunctionDef, self.generic_visit(node))
        _check_attribute_name(node.name)

        if node.decorator_list:
            raise SyntaxError("unsafe node: decorators")

        return node

    def explore_arg(self, node: ast.arg) -> ast.arg:
        node = cast(ast.arg, self.generic_visit(node))
        _check_attribute_name(node.arg)
        return node

    def explore_keyword(self, node: ast.keyword) -> ast.keyword:
        node = cast(ast.keyword, self.generic_visit(node))

        if node.arg:
            _check_attribute_name(node.arg)

        return node

    def explore_arguments(self, node: ast.arguments) -> ast.arguments:
        node = cast(ast.arguments, self.generic_visit(node))
        if node.vararg or node.kwarg:
            raise SyntaxError("unsafe node: variadic keyword arguments")
        return node

    def explore_Name(self, node: ast.Name) -> ast.Name:
        node = cast(ast.Name, self.generic_visit(node))
        _check_attribute_name(node.id)
        return node

    def explore_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        node = cast(ast.Attribute, self.generic_visit(node))
        _check_attribute_name(node.attr)
        return ast.Attribute(
            value=call_wrapper(node.value),
            attr=node.attr,
            ctx=node.ctx,
        )

    def explore_Call(self, node: ast.Call) -> ast.Call:
        node = cast(ast.Call, self.generic_visit(node))

        kwkeys = []
        kwvalues = []

        for kw in node.keywords:
            if isinstance(kw.value, ast.Dict) and kw.arg is None:
                kwkeys += kw.value.keys
                kwvalues += kw.value.values
            else:
                kwkeys.append(ast.Constant(kw.arg))
                kwvalues.append(kw.value)

        return ast.Call(
            func=ast.Name("__call_checker", ctx=ast.Load()),
            args=[],
            keywords=[
                ast.keyword(arg="__func", value=node.func),
                ast.keyword(
                    arg="__args", value=ast.List(elts=node.args, ctx=ast.Load())
                ),
                ast.keyword(
                    arg="__kwargs",
                    value=ast.Dict(keys=kwkeys, values=kwvalues, ctx=ast.Load()),
                ),
            ],
        )

    def explore_SetComp(self, node: ast.SetComp) -> ast.SetComp:
        node = cast(ast.SetComp, self.generic_visit(node))
        stores = [
            n.id
            for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        ]
        return cast(ast.SetComp, StoreChecker(stores).visit(node))

    def explore_DictComp(self, node: ast.DictComp) -> ast.DictComp:
        node = cast(ast.DictComp, self.generic_visit(node))
        stores = [
            n.id
            for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        ]
        return cast(ast.DictComp, StoreChecker(stores).visit(node))

    def explore_GeneratorExp(self, node: ast.GeneratorExp) -> ast.GeneratorExp:
        node = cast(ast.GeneratorExp, self.generic_visit(node))
        stores = [
            n.id
            for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        ]
        return cast(ast.GeneratorExp, StoreChecker(stores).visit(node))

    def explore_ListComp(self, node: ast.ListComp) -> ast.ListComp:
        node = cast(ast.ListComp, self.generic_visit(node))
        stores = [
            n.id
            for n in ast.walk(node)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        ]
        return cast(ast.ListComp, StoreChecker(stores).visit(node))

    def explore_Subscript(self, node: ast.Subscript) -> ast.Subscript:
        node = cast(ast.Subscript, self.generic_visit(node))

        return ast.Subscript(
            value=call_wrapper(cast(ast.AST, node.value)),
            slice=node.slice,
            ctx=node.ctx,
        )

    def explore_Assign(self, node: ast.Assign) -> list[ast.Assign | ast.Expr]:
        node = cast(ast.Assign, self.generic_visit(node))

        nodes: list[ast.Assign | ast.Expr] = [node]
        for target in node.targets:
            for n in ast.walk(cast(ast.AST, target)):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    nodes.append(
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Name("__type_checker", ctx=ast.Load()),
                                args=[],
                                keywords=[ast.keyword(arg="__obj", value=n)],
                            )
                        )
                    )
        return nodes

    def explore_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        node = cast(ast.ExceptHandler, self.generic_visit(node))
        if node.name:
            _check_attribute_name(node.name)

        return node

    def explore_For(self, node: ast.For) -> ast.For:
        node = cast(ast.For, self.generic_visit(node))

        node.iter = ast.Call(
            func=ast.Name("__type_checker", ctx=ast.Load()),
            args=[],
            keywords=[
                ast.keyword(arg="__obj", value=node.iter),
            ],
        )

        for n in ast.walk(cast(ast.AST, node.target)):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                node.body.insert(
                    0,
                    ast.Expr(
                        value=ast.Call(
                            func=ast.Name("__type_checker", ctx=ast.Load()),
                            args=[],
                            keywords=[ast.keyword(arg="__obj", value=n)],
                        )
                    ),
                )

        return node


# --- Public Functions --------------------------------------------------------


def const_eval(expr: str | bytes) -> Any:
    """const_eval(expression) -> value

    Safe Python constant evaluation

    Evaluates a string that contains an expression describing
    a Python constant. Strings that are not valid Python expressions
    or that contain other code besides the constant raise ValueError.

    >>> const_eval("10")
    10
    >>> const_eval("[1,2, (3,4), {'foo':'bar'}]")
    [1, 2, (3, 4), {'foo': 'bar'}]
    >>> const_eval("1+2")
    Traceback (most recent call last):
    ...
    """
    if isinstance(expr, bytes):
        expr = expr.decode()

    if not isinstance(expr, str):
        raise TypeError(f"expr_eval expects a string, got {type(expr)}")

    return ast.literal_eval(expr)


def expr_eval(expr: str | bytes) -> Any:
    """expr_eval(expression) -> value
    Restricted Python expression evaluation
    Evaluates a string that contains an expression that only
    uses Python constants. This can be used to e.g. evaluate
    a numerical expression from an untrusted source.
    >>> expr_eval("1+2")
    3
    >>> expr_eval("[1,2]*2")
    [1, 2, 1, 2]
    >>> expr_eval("__import__('sys').modules")
    Traceback (most recent call last):
    ...
    SyntaxError: Nodes of type Name are not allowed
    """
    if isinstance(expr, bytes):
        expr = expr.decode()

    if not isinstance(expr, str):
        raise TypeError(f"expr_eval expects a string, got {type(expr)}")

    code = ast.unparse(CodeChecker(_AST_MATH_NODES).visit(ast.parse(expr)))
    return unsafe_eval(code)


def allow_instance(t: type) -> type:
    """Allow an instance to be used in the evaluation context

    Args:
        t (type): The instance to be allowed

    Returns:
        type: The instance that is allowed
    """
    global _wrapped_instances  # noqa: PLW0603 (Reason: we need to modify the global variable, check docstring) # pylint: disable=global-statement

    _wrapped_instances += (t,)
    return t


def allow_type(t: type) -> type:
    """Allow a type to be used in the evaluation context

    Args:
        t (type): The type to be allowed

    Returns:
        type: The type that is allowed
    """
    global _wrapped_types  # noqa: PLW0603 (Reason: we need to modify the global variable, check docstring) # pylint: disable=global-statement

    _wrapped_types = _wrapped_types + (t,)
    return allow_instance(t)


def test_python_expr(expr: str, mode: str = "eval") -> str | bool:
    """Test a Python expression before evaluating it

    Args:
        expr (str | bytes): A Python expression
        mode (str): The mode of the expression (eval, exec)

    Returns:
        str | bool: An error message if the expression is not safe, False otherwise
    """

    if isinstance(expr, bytes):
        expr = expr.decode()

    if not isinstance(expr, str):
        raise TypeError(f"safe_eval expects a string, got {type(expr)}")

    try:
        wrapped_expr = ast.unparse(
            CodeChecker(_AST_ALLOWED_NODES).visit(ast.parse(expr))
        )
        compile(wrapped_expr, "<sandbox>", mode)
    except (TypeError, NameError, SyntaxError, ValueError) as err:
        if len(err.args) >= 2 and len(err.args[1]) >= 4:
            error = {
                "message": err.args[0],
                "filename": err.args[1][0],
                "lineno": err.args[1][1],
                "offset": err.args[1][2],
                "error_line": err.args[1][3],
            }

            msg = f"{type(err).__name__} : {error['message']} at line {error['lineno']}\n{error['error_line']}"
        else:
            msg = f"{err}"
        return msg
    return False


def safe_eval(
    expr: str | bytes,
    globals_dict: Optional[ContextType] = None,
    locals_dict: Optional[ContextType] = None,
    mode: Literal["eval", "exec"] = "eval",
    filename: Optional[str] = None,
    locals_builtins: bool = False,
    sandbox_instances: OptionalTuple[type] = (),
    sandbox_types: OptionalTuple[type] = (),
    nocopy: Optional[bool] = None,
    ast_subset: (
        frozenset[type[ast.AST]] | tuple[type[ast.AST], ...]
    ) = _AST_ALLOWED_NODES,  # pylint: disable=bad-whitespace
):
    def sanitize_context(context: ContextType):
        to_remove = [k for k in context if "__" in k]
        for k in to_remove:
            del context[k]

    if nocopy is not None:
        _logger.warning("safe_eval: nocopy parameter is deprecated, defaulting to True")

    if isinstance(expr, bytes):
        expr = expr.decode()
    elif not isinstance(expr, str):
        raise TypeError(f"safe_eval expects a string, got {type(expr)}")

    for node in ast_subset:
        if node not in _AST_ALLOWED_NODES:
            raise ValueError(f"unsafe node: {node.__name__} (node not allowed)")

    globals_dict_eval: ContextType
    if globals_dict is None:
        globals_dict_eval = {}
    elif isinstance(globals_dict, dict):
        globals_dict_eval = globals_dict.copy()
        sanitize_context(globals_dict_eval)
    else:
        raise TypeError(f"globals_dict must be a dict, got {type(globals_dict)}")

    locals_dict_eval: Optional[ContextType]
    if locals_builtins and locals_dict is None:
        locals_dict_eval = {}
    elif locals_dict is not None:
        locals_dict_eval = locals_dict.copy()
        sanitize_context(locals_dict_eval)
    else:
        locals_dict_eval = None

    globals_dict_eval.update(_prepare_environment(sandbox_types, sandbox_instances))
    globals_dict_eval["__builtins__"] = _BUILTINS.copy()
    code = ast.unparse(
        CodeChecker(ast_subset).visit(ast.parse(expr.strip(), mode=mode))
    )

    c = compile(code, filename or "<sandbox>", mode)
    try:
        ret = unsafe_eval(c, globals_dict_eval, locals_dict_eval)
    except odoo.exceptions.UserError:
        raise
    except odoo.exceptions.RedirectWarning:
        raise
    except werkzeug.exceptions.HTTPException:
        raise
    except OperationalError:
        # Do not hide PostgreSQL low-level exceptions, to let the auto-replay
        # of serialized transactions work its magic
        raise
    except ZeroDivisionError:
        raise
    except Exception as e:
        raise ValueError(f"{type(e)} : {e} while evaluating\n{expr}")

    if globals_dict is not None:
        globals_dict.update(globals_dict_eval)
        sanitize_context(globals_dict)

    if locals_dict is not None:
        locals_dict.update(locals_dict_eval or {})
        sanitize_context(locals_dict)

    if mode == "eval":
        return ret


# --- Modules safe overrides ---------------------------------------------------

vanilla_type_checker = _prepare_environment((), ())["__type_checker"]

json = SafeWrapper(__obj=__import__("json"), __type_checker=vanilla_type_checker)
time = SafeWrapper(__obj=__import__("time"), __type_checker=vanilla_type_checker)
pytz = SafeWrapper(__obj=__import__("pytz"), __type_checker=vanilla_type_checker)
dateutil = SafeWrapper(
    __obj=__import__("dateutil"), __type_checker=vanilla_type_checker
)
datetime = SafeWrapper(
    __obj=__import__("datetime"), __type_checker=vanilla_type_checker
)  # type: ignore
