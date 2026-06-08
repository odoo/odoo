import ast
from contextlib import contextmanager

from odoo.models import BaseModel
from odoo.tools import BinaryBytes
from odoo.tools.safe_eval import _BUILTINS as _SAFE_EVAL_BUILTINS

_ALLOWED_EVAL_KWARG_TYPES = (
    type(None),
    bool,
    int,
    float,
    str,
    bytes,
    BaseModel,
    BinaryBytes,
)


class _Scope(set[str]):
    """Set of names bound in one visitor scope."""
    __slots__ = ('is_comprehension',)

    def __init__(self, iterable=(), *, is_comprehension: bool = False):
        super().__init__(iterable)
        self.is_comprehension = is_comprehension


class _UndefinedNameCollector(ast.NodeVisitor):
    """Collect names loaded from an expression but not bound inside it."""

    def __init__(self):
        self.undefined_names = set()
        self.scopes = [_Scope()]

    def is_bound(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self.scopes))

    def bind(self, name: str, *, named_expr: bool = False) -> None:
        """
        Bind one name in the right scope.

        Named expressions inside comprehensions bind in the nearest outer
        non-comprehension scope, not in the comprehension-local scope.
        """
        if named_expr:
            for scope in reversed(self.scopes):
                if not scope.is_comprehension:
                    scope.add(name)
                    return
        self.scopes[-1].add(name)

    def bind_target(self, target: ast.AST, *, named_expr: bool = False) -> None:
        """Bind all names introduced by an assignment target."""
        if isinstance(target, ast.Name):
            self.bind(target.id, named_expr=named_expr)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self.bind_target(elt, named_expr=named_expr)
        elif isinstance(target, ast.Starred):
            self.bind_target(target.value, named_expr=named_expr)

    def bind_arguments(self, args: ast.arguments) -> None:
        """Bind arguments of a function."""
        for arg in args.posonlyargs:
            self.bind(arg.arg)
        for arg in args.args:
            self.bind(arg.arg)
        if args.vararg:
            self.bind(args.vararg.arg)
        for arg in args.kwonlyargs:
            self.bind(arg.arg)
        if args.kwarg:
            self.bind(args.kwarg.arg)

    def visit_Name(self, node: ast.Name) -> None:
        if (
            isinstance(node.ctx, ast.Load)
            and node.id not in _SAFE_EVAL_BUILTINS
            and not self.is_bound(node.id)
        ):
            self.undefined_names.add(node.id)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self.bind_target(node.target, named_expr=True)

    def _visit_comprehension(self, expr_nodes: list[ast.AST], generators: list[ast.comprehension]) -> None:
        """Visit a comprehension using Python's evaluation order and scope."""
        first, *rest = generators
        self.visit(first.iter)

        with self.new_scope(is_comprehension=True):
            self.bind_target(first.target)
            for if_clause in first.ifs:
                self.visit(if_clause)

            for generator in rest:
                self.visit(generator.iter)
                self.bind_target(generator.target)
                for if_clause in generator.ifs:
                    self.visit(if_clause)

            for expr_node in expr_nodes:
                self.visit(expr_node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    visit_SetComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension([node.key, node.value], node.generators)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # Defaults are bound to the outer scope of the lambda.
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)

        with self.new_scope():
            self.bind_arguments(node.args)
            self.visit(node.body)

    @contextmanager
    def new_scope(self, *, is_comprehension: bool = False):
        scope = _Scope(is_comprehension=is_comprehension)
        self.scopes.append(scope)
        try:
            yield scope
        finally:
            self.scopes.pop()


def get_undefined_names(expr: str) -> set[str]:
    """Return the external names required to evaluate ``expr``.

    :param expr: Python expression parsed in ``eval`` mode.
    :return: Names loaded by the expression but not bound inside it.

    Example:
        >>> get_undefined_names("a + b")
        {'a', 'b'}
        >>> get_undefined_names("(z := x) + z")
        {'x'}
        >>> get_undefined_names("[x + y for x in xs if y > 0]")
        {'xs', 'y'}
    """
    collector = _UndefinedNameCollector()
    collector.visit(ast.parse(expr, mode="eval"))
    return collector.undefined_names


def check_eval_kwargs(kwargs) -> None:
    """Validate kwargs passed to safe-eval-generated callables.

    :param kwargs: Keyword arguments that will be passed into an evaluated callable.
    :raise TypeError: If a value is not part of the safe, expected value set.
    """

    def is_safe(val) -> bool:
        if isinstance(val, _ALLOWED_EVAL_KWARG_TYPES):
            return True

        if isinstance(val, (list, tuple)):
            return all(is_safe(item) for item in val)

        if isinstance(val, dict):
            return all(
                isinstance(key, str) and is_safe(item)
                for key, item in val.items()
            )

        return False

    for name, value in kwargs.items():
        if not is_safe(value):
            raise TypeError(
                f"Unsafe eval kwarg {name!r}: {type(value).__name__}",
            )
