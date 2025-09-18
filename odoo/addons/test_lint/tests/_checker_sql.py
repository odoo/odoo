"""SQL injection checker using stdlib ``ast``.

Detects unsafe string construction in ``cr.execute()``, ``cr.executemany()``,
and ``SQL()`` calls by recursively evaluating whether the query argument is
a compile-time constant expression.

Replaces the former ``_odoo_checker_sql_injection.py`` (which required
``astroid`` + ``pylint``).  All logic is equivalent; the test suite in
``test_checkers.py`` validates parity.

Inspired by the OCA/pylint-odoo project.
Thanks @moylop260 (Moisés López) & @nilshamerlinck (Nils Hamerlinck).
"""

import ast
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# Cursor expression chains that indicate a cr.execute() call.
CURSOR_EXPRESSIONS = frozenset(
    {
        "self.env.cr",
        "self.cr",
        "cr",
        "odoo.tools",
        "tools",
    }
)

# Attribute names (or chains) considered safe in SQL construction.
ATTRIBUTE_WHITELIST = ("_table", "name", "lang", "id", "get_lang.code")

# Function names whose return values are considered safe.
FUNCTION_WHITELIST = frozenset(
    {
        "create",
        "read",
        "write",
        "browse",
        "select",
        "get",
        "strip",
        "items",
        "_select",
        "_from",
        "_where",
        "any",
        "join",
        "split",
        "tuple",
        "get_sql",
        "search",
        "list",
        "set",
        "next",
        "SQL",
    }
)


@dataclass
class Violation:
    """A single SQL injection warning."""

    lineno: int
    col_offset: int
    message: str = ""


@dataclass
class SqlInjectionChecker:
    """Check a single Python module AST for SQL injection risks.

    Usage::

        checker = SqlInjectionChecker("path/to/file.py")
        violations = list(checker.check(ast.parse(source)))
    """

    filepath: str

    # Per-file state: function defs and call sites for cross-function tracking.
    _function_defs: dict[str, list[ast.FunctionDef]] = field(
        default_factory=lambda: defaultdict(list),
        init=False,
    )
    _callsites: dict[str, list[tuple[int | None, bool, ast.Call]]] = field(
        default_factory=lambda: defaultdict(list),
        init=False,
    )
    _root_call: ast.Call | None = field(default=None, init=False)
    _const_def_cache: dict = field(default_factory=dict, init=False)

    # ── Public API ──────────────────────────────────────────────────

    def check(self, tree: ast.Module) -> Iterator[Violation]:
        """Walk *tree* and yield SQL injection violations."""
        yield from self._walk(tree)

    # ── AST Walking ─────────────────────────────────────────────────

    def _walk(self, node: ast.AST) -> Iterator[Violation]:
        """Depth-first walk, dispatching to visitors."""
        match node:
            case ast.Call():
                yield from self._visit_call(node)
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                yield from self._visit_functiondef(node)
        for child in ast.iter_child_nodes(node):
            yield from self._walk(child)

    def _visit_call(self, node: ast.Call) -> Iterator[Violation]:
        """Check ``cr.execute()``, ``SQL()`` etc. calls."""
        if self._check_sql_injection_risky(node):
            yield Violation(node.lineno, node.col_offset)

    def _visit_functiondef(self, node: ast.FunctionDef) -> Iterator[Violation]:
        """Record function definitions and re-evaluate earlier call sites."""
        if Path(self.filepath).name.startswith("test_"):
            return

        self._function_defs[node.name].append(node)

        for position, const_args, call in self._callsites[node.name]:
            if not self._is_const_def(node, position=position, const_args=const_args):
                yield Violation(
                    node.lineno,
                    node.col_offset,
                    f"because it is used to build a query at {self.filepath}:{call.lineno}",
                )

    # ── SQL Injection Detection ─────────────────────────────────────

    def _check_sql_injection_risky(self, node: ast.Call) -> bool:
        """Return True if *node* is a risky SQL call."""
        if Path(self.filepath).name.startswith("test_"):
            return False

        if not node.args:
            return False

        # Check if this is a cursor.execute/SQL call
        match node.func:
            case ast.Attribute(attr=attr) if attr in (
                "execute",
                "executemany",
                "SQL",
            ):
                if self._get_cursor_name(node.func) not in CURSOR_EXPRESSIONS:
                    return False
            case ast.Name(id="SQL"):
                pass
            case _:
                return False

        first_arg = node.args[0]
        result = self._check_concatenation(first_arg)
        if result is not None:
            return result
        return True

    def _check_concatenation(self, node: ast.expr) -> bool | None:
        """Check if *node* is an unsafe string construction.

        Returns True (injection), False (safe), or None (unknown/not applicable).
        """
        node = self._resolve(node)

        if self._allowable(node):
            return False

        match node:
            case ast.BinOp(op=ast.Mod() | ast.Add()):
                match node.right:
                    case ast.Tuple(elts=elts):
                        if not all(map(self._allowable, elts)):
                            return True
                    case ast.Dict(values=values):
                        if not all(map(self._allowable, values)):
                            return True
                    case _ if not self._allowable(node.right):
                        return True
                return self._check_concatenation(node.left)

            case ast.Call(func=ast.Attribute(attr="format")):
                return not (
                    all(map(self._allowable, node.args or []))
                    and all(self._allowable(kw.value) for kw in (node.keywords or []))
                )

            case ast.JoinedStr(values=values):
                return not all(
                    self._allowable(fv.value)
                    for fv in values
                    if isinstance(fv, ast.FormattedValue)
                )

        return None

    def _resolve(self, node: ast.expr) -> ast.expr:
        """If *node* is a Name, try to find its simple assignment value.

        Tuple-unpack assignments (``a, b = ...``) are intentionally skipped
        here because position context is needed for correct resolution.
        Those are handled by :meth:`_check_name_constexpr` instead.
        """
        if isinstance(node, ast.Name):
            scope = self._find_enclosing_scope(node)
            if scope is not None:
                for target_node in self._find_assignments(scope, node.id):
                    if isinstance(target_node, ast.Assign):
                        if any(isinstance(t, ast.Tuple) for t in target_node.targets):
                            continue
                        return target_node.value
        return node

    # ── Constant Expression Analysis ────────────────────────────────

    def _is_constexpr(
        self,
        node: ast.expr,
        *,
        args_allowed: bool = False,
        position: int | None = None,
    ) -> bool:
        """Recursively evaluate whether *node* is a compile-time constant."""
        match node:
            case ast.Constant():
                return True

            case ast.List(elts=elts) | ast.Set(elts=elts):
                return self._all_const(elts, args_allowed=args_allowed)

            case ast.Tuple(elts=elts):
                if position is not None:
                    return self._is_constexpr(
                        elts[position],
                        args_allowed=args_allowed,
                    )
                return self._all_const(elts, args_allowed=args_allowed)

            case ast.Dict(keys=keys, values=values):
                return all(
                    self._is_constexpr(k, args_allowed=args_allowed)
                    and self._is_constexpr(v, args_allowed=args_allowed)
                    for k, v in zip(keys, values, strict=False)
                )

            case ast.Starred(value=value):
                return self._is_constexpr(
                    value,
                    args_allowed=args_allowed,
                    position=position,
                )

            case ast.BinOp(op=op, left=left, right=right):
                left_ok = self._is_constexpr(left, args_allowed=args_allowed)
                # %d formatting is always safe (integer only)
                if (
                    isinstance(op, ast.Mod)
                    and isinstance(left, ast.Constant)
                    and isinstance(left.value, str)
                    and "%d" in left.value
                    and "%s" not in left.value
                ):
                    return True
                right_ok = self._is_constexpr(right, args_allowed=args_allowed)
                return left_ok and right_ok

            case ast.Name(id=name):
                return self._check_name_constexpr(
                    node,
                    name,
                    args_allowed=args_allowed,
                )

            case ast.JoinedStr(values=values):
                return self._all_const(
                    (
                        fv.value
                        for fv in values
                        if isinstance(fv, ast.FormattedValue)
                        if not (
                            isinstance(fv.value, ast.Attribute)
                            and fv.value.attr.startswith("_")
                        )
                    ),
                    args_allowed=args_allowed,
                    position=position,
                )

            case ast.Call(func=ast.Attribute(attr="append"), args=[first_arg]):
                return self._is_constexpr(first_arg)

            case ast.Call(func=ast.Attribute(attr="format", value=receiver)):
                return (
                    self._is_constexpr(receiver, args_allowed=args_allowed)
                    and self._all_const(node.args, args_allowed=args_allowed)
                    and self._all_const(
                        (kw.value for kw in node.keywords or []),
                        args_allowed=args_allowed,
                    )
                )

            case ast.Call():
                old_root = self._root_call
                if self._root_call is None:
                    self._root_call = node
                try:
                    return self._evaluate_function_call(
                        node,
                        args_allowed=args_allowed,
                        position=position,
                    )
                finally:
                    self._root_call = old_root

            case ast.IfExp(body=body, orelse=orelse):
                return self._is_constexpr(
                    body, args_allowed=args_allowed
                ) and self._is_constexpr(orelse, args_allowed=args_allowed)

            case ast.Subscript(value=value):
                return self._is_constexpr(value, args_allowed=args_allowed)

            case ast.BoolOp(values=values):
                return self._all_const(values, args_allowed=args_allowed)

            case ast.Attribute():
                return self._check_attribute_whitelist(node)

        return False

    def _all_const(self, nodes, *, args_allowed=False, position=None) -> bool:
        """Return True if all *nodes* are constant expressions."""
        return all(
            self._is_constexpr(n, args_allowed=args_allowed, position=position)
            for n in nodes
        )

    # ── Name Resolution ─────────────────────────────────────────────

    def _check_name_constexpr(
        self,
        node: ast.Name,
        name: str,
        *,
        args_allowed: bool = False,
    ) -> bool:
        """Evaluate whether a variable reference resolves to a constant."""
        scope = self._find_enclosing_scope(node)
        if scope is None:
            return False

        assigned_results: list[bool] = []

        for assign_node in self._find_assignments(scope, name):
            match assign_node:
                case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.arg():
                    # Variable comes from function parameter
                    assigned_results.append(args_allowed)

                case ast.Assign(value=value, targets=targets):
                    # Check if the name is part of a tuple unpack
                    target_position = self._find_tuple_position(targets, name)
                    if target_position is not None:
                        assigned_results.append(
                            self._is_constexpr(
                                value,
                                args_allowed=args_allowed,
                                position=target_position,
                            )
                        )
                    else:
                        assigned_results.append(
                            self._is_constexpr(value, args_allowed=args_allowed)
                        )

                case ast.AugAssign(value=value):
                    # Only check the RHS value.  The target's base constness
                    # is covered by the initial assignment(s) that
                    # ``_find_assignments`` also yields.  Checking the target
                    # here would recurse infinitely (the target name is the
                    # same variable we are already evaluating).
                    assigned_results.append(
                        self._is_constexpr(value, args_allowed=args_allowed)
                    )

                case ast.For(iter=iter_node):
                    assigned_results.append(
                        self._is_constexpr(iter_node, args_allowed=args_allowed)
                    )

                case ast.comprehension(iter=iter_node):
                    assigned_results.append(
                        self._is_constexpr(iter_node, args_allowed=args_allowed)
                    )

                case ast.Module():
                    return True

        if assigned_results and all(assigned_results):
            return True
        return self._is_asserted(scope, name)

    def _find_tuple_position(self, targets: list[ast.expr], name: str) -> int | None:
        """Return the index of *name* in a tuple-unpack target, or None."""
        for target in targets:
            if isinstance(target, ast.Tuple):
                for i, elt in enumerate(target.elts):
                    if isinstance(elt, ast.Name) and elt.id == name:
                        return i
        return None

    # ── Function Call Evaluation ────────────────────────────────────

    def _evaluate_function_call(
        self,
        node: ast.Call,
        *,
        args_allowed: bool = False,
        position: int | None = None,
    ) -> bool:
        """Evaluate whether a function call returns a safe value."""
        match node.func:
            case ast.Attribute(attr=name):
                pass
            case ast.Name(id=name):
                pass
            case _:
                return False

        if name == "SQL":
            return True
        # Recursive call to same function → assume safe to avoid infinite loop
        scope = self._find_enclosing_scope(node)
        if isinstance(scope, ast.FunctionDef) and name == scope.name:
            return True

        const_args = self._all_const(node.args, args_allowed=args_allowed)

        # Record call site for later re-evaluation when function def is found
        if self._root_call is not None:
            self._callsites[name].append((position, const_args, self._root_call))

        if funs := self._function_defs[name]:
            return all(
                self._is_const_def(fun, position=position, const_args=const_args)
                for fun in funs
            )
        return True

    def _is_const_def(
        self,
        node: ast.FunctionDef,
        *,
        position: int | None = None,
        const_args: bool = False,
    ) -> bool:
        """Check whether a function always returns a constant expression."""
        cache_key = (id(node), position, const_args)
        if cache_key in self._const_def_cache:
            return self._const_def_cache[cache_key]

        if node.name.startswith("__") or node.name in FUNCTION_WHITELIST:
            self._const_def_cache[cache_key] = True
            return True

        result = all(
            self._is_constexpr(
                ret.value,
                args_allowed=const_args,
                position=position,
            )
            for ret in self._find_return_nodes(node)
            if ret.value is not None
        )
        self._const_def_cache[cache_key] = result
        return result

    # ── Allowability ────────────────────────────────────────────────

    def _allowable(self, node: ast.expr) -> bool:
        """Return True if *node* is safe to include in SQL construction."""
        # Private functions are trusted
        scope = self._find_enclosing_scope(node)
        if isinstance(scope, ast.FunctionDef) and (
            scope.name.startswith("_") or scope.name == "init"
        ):
            return True

        # Name-based psycopg check (replaces astroid safe_infer)
        if self._looks_like_psycopg(node):
            return True

        if self._is_constexpr(node):
            return True

        # self._thing is always OK (mostly self._table)
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.attr.startswith("_")
        )

    def _check_attribute_whitelist(self, node: ast.Attribute) -> bool:
        """Check if an attribute access chain is whitelisted."""
        chain = self._get_attribute_chain(node)
        while chain:
            if chain in ATTRIBUTE_WHITELIST or chain.startswith("_"):
                return True
            if "." in chain:
                _, chain = chain.split(".", 1)
            else:
                break
        return False

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _get_attribute_chain(node: ast.expr) -> str:
        """Build a dotted name string from an attribute access chain."""
        match node:
            case ast.Attribute(value=value, attr=attr):
                prefix = SqlInjectionChecker._get_attribute_chain(value)
                return f"{prefix}.{attr}" if prefix else attr
            case ast.Name(id=name):
                return name
            case ast.Call(func=func):
                return SqlInjectionChecker._get_attribute_chain(func)
        return ""

    @staticmethod
    def _get_cursor_name(node: ast.Attribute) -> str:
        """Build the cursor expression chain (e.g. ``self.env.cr``)."""
        parts: list[str] = []
        current = node.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        parts.reverse()
        return ".".join(parts)

    @staticmethod
    def _find_enclosing_scope(node: ast.AST) -> ast.AST | None:
        """Walk up the AST to find the enclosing function/module scope.

        Requires ``ast.fix_missing_locations`` or a parent-annotated tree.
        """
        current = getattr(node, "_parent", None)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                return current
            current = getattr(current, "_parent", None)
        return None

    @staticmethod
    def _find_assignments(scope: ast.AST, name: str) -> Iterator[ast.AST]:
        """Find all nodes in *scope* that assign to *name*.

        Yields the **statement** node (Assign, AugAssign, For, etc.) or the
        FunctionDef/arg node if the name comes from parameters.
        """
        # Check function parameters first
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in scope.args.args + scope.args.kwonlyargs:
                if arg.arg == name:
                    yield scope
                    return
            if scope.args.vararg and scope.args.vararg.arg == name:
                yield scope
                return
            if scope.args.kwarg and scope.args.kwarg.arg == name:
                yield scope
                return

        for node in ast.walk(scope):
            match node:
                case ast.Assign(targets=targets):
                    for target in targets:
                        if isinstance(target, ast.Name) and target.id == name:
                            yield node
                        elif isinstance(target, ast.Tuple):
                            for elt in target.elts:
                                if isinstance(elt, ast.Name) and elt.id == name:
                                    yield node
                case ast.AugAssign(target=ast.Name(id=target_name)) if (
                    target_name == name
                ):
                    yield node
                case ast.For(target=target):
                    if isinstance(target, ast.Name) and target.id == name:
                        yield node
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name) and elt.id == name:
                                yield node
                case ast.comprehension(target=target):
                    if isinstance(target, ast.Name) and target.id == name:
                        yield node

    @staticmethod
    def _find_return_nodes(node: ast.AST) -> list[ast.Return]:
        """BFS for all Return nodes inside *node*."""
        return [child for child in ast.walk(node) if isinstance(child, ast.Return)]

    @staticmethod
    def _is_asserted(scope: ast.AST, name: str) -> bool:
        """Check if *name* is referenced in any ``assert`` within *scope*."""
        for node in ast.walk(scope):
            if isinstance(node, ast.Assert) and node.test is not None:
                for child in ast.walk(node.test):
                    if isinstance(child, ast.Name) and child.id == name:
                        return True
        return False

    @staticmethod
    def _looks_like_psycopg(node: ast.expr) -> bool:
        """Heuristic: does *node* look like a psycopg SQL object?

        Replaces ``astroid.utils.safe_infer()`` with a name-based check.
        """
        match node:
            case ast.Call(func=ast.Attribute(attr="format", value=value)):
                return SqlInjectionChecker._looks_like_psycopg(value)
            case ast.Call(func=ast.Attribute(value=ast.Name(id=name))):
                return name in ("sql", "psycopg2", "psycopg")
            case ast.Call(func=ast.Name(id="SQL")):
                return True
            case ast.Name(id=name):
                return name == "SQL"
        return False


def annotate_parents(tree: ast.AST) -> None:
    """Add ``_parent`` attribute to every node in the AST.

    Required by :meth:`SqlInjectionChecker._find_enclosing_scope`.
    """
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node


def check_file(filepath: str, source: bytes | str | None = None) -> list[Violation]:
    """Convenience: check a single file for SQL injection risks.

    :param filepath: Path to the Python file.
    :param source: Optional source code; read from *filepath* if not given.
    """
    if source is None:
        source = Path(filepath).read_bytes()
    try:
        tree = ast.parse(source, filepath)
    except SyntaxError:
        return []
    annotate_parents(tree)
    checker = SqlInjectionChecker(filepath)
    return list(checker.check(tree))
