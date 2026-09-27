import ast
import enum
import fnmatch
import logging
import os

from odoo.tools import config
from odoo.tools.misc import StackMap

from .common import LintCase, Manifest, opj

_logger = logging.getLogger(__name__)


class Tag(enum.Enum):
    TYPE_SQL = enum.auto()  # odoo.tools.SQL
    EXECUTE_SQL = enum.auto()  # Callable[[str | SQL, ...], ...]
    RETURN_SQL = enum.auto()  # Callable[..., SQL]
    RETURN_SAFE_ARG = enum.auto()  # Callable[..., Safe]
    CURSOR = enum.auto()  # instance of Cursor
    SQL = enum.auto()  # instance of SQL
    SAFE_ARG = enum.auto()  # a string, integer, etc.

    @staticmethod
    def merge(a, b):
        if a == b:
            return a
        if not a or not b:
            return None
        for a, b in ((a, b), (b, a)):
            if (
                (a == Tag.TYPE_SQL and b == Tag.EXECUTE_SQL)
                or (b == Tag.TYPE_SQL and a == Tag.RETURN_SQL)  # logically inverse, but we want to check arguments
                or (a in (Tag.TYPE_SQL, Tag.RETURN_SQL) and b == Tag.RETURN_SAFE_ARG)
                or (a == Tag.SQL and b == Tag.SAFE_ARG)
            ):
                return b
        return None  # unknown


class SQLInjectionLinter(ast.NodeVisitor):
    """Check the use of ``odoo.tools.SQL`` and cursor's execute methods
    (execute, executemany, execute_values) including their parameter."""
    def __init__(self):
        self._reset()

    def _reset(self):
        self.vars = StackMap({})
        self.result_type = None
        self.in_def_function = 0

    def add_error(self, node):
        pass

    def _merge_vars(self, *envs):
        merged = self.vars
        for env in envs:
            for name, typ in env.items():
                if name in merged:
                    typ = Tag.merge(merged[name], typ)
                merged[name] = typ

    def visit_Module(self, node):
        # Usual entry-point
        self._reset()
        self.generic_visit(node)

    def generic_visit(self, node):
        super().generic_visit(node)
        if isinstance(node, ast.expr):
            self.result_type = None

    # The call check

    def visit_Call(self, node):
        self.visit(node.func)
        # result type and what to check
        if isinstance(node.func, ast.Name) and node.func.id == 'isinstance':
            invalid_arg_types = ()
        else:
            invalid_arg_types = (Tag.TYPE_SQL, Tag.EXECUTE_SQL)
        check_call = 0
        if self.result_type == Tag.RETURN_SQL:
            result_type = Tag.SQL
        elif self.result_type == Tag.RETURN_SAFE_ARG:
            result_type = Tag.SAFE_ARG
        elif self.result_type == Tag.TYPE_SQL:
            result_type = Tag.SQL
            check_call = 1
        elif self.result_type == Tag.EXECUTE_SQL:
            result_type = None
            check_call = 1
        else:
            result_type = None
        # check keywords then arguments
        for kw in node.keywords:
            self.visit(kw.value)
            if check_call and not node.args and (kw.arg is None or kw.arg == 'query'):
                # execute(**kw)
                # execute(query=...)
                self.add_error(node)
                check_call = 0  # stop checking
            elif self.result_type in invalid_arg_types:
                # call(..., q=SQL) - see below
                self.add_error(node)
        for arg in node.args:
            self.visit(arg)
            if check_call > 0 and self.result_type not in (Tag.SQL, Tag.SAFE_ARG):
                self.add_error(node)
                check_call = 0  # stop checking
            elif self.result_type in invalid_arg_types:
                # call(..., SQL, ...)
                # except for isinstance(..., SQL)
                self.add_error(node)
            check_call -= 1
        self.result_type = result_type

    # Assignments

    def visit_Return(self, node):
        if node.value is None:
            return
        self.visit(node.value)
        self._merge_vars({'$return': self.result_type})

    def visit_Assign(self, node):
        self.visit(node.value)

        result_type = self.result_type if len(node.targets) == 1 else None
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.vars[target.id] = result_type

    def visit_AugAssign(self, node):
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self._merge_vars({node.target.id: self.result_type})
            self.result_type = self.vars[node.target.id]
        else:
            self.result_type = None  # not determined

    def visit_NamedExpr(self, node):
        self.visit_AugAssign(node)  # same implementation

    def visit_AnnAssign(self, node):
        if node.value:
            self.visit(node.value)
            if isinstance(node.target, ast.Name):
                self.vars[node.target.id] = self.result_type

    # Asserting a type

    def visit_Assert(self, node):
        # check if we have an instance of SQL
        if (
            isinstance(t := node.test, ast.Call)
            and isinstance(name := t.func, ast.Name)
            and name.id == 'isinstance'
            and len(t.args) == 2
            and isinstance(var := t.args[0], ast.Name)
        ):
            self.visit(t.args[1])
            if self.result_type == Tag.TYPE_SQL:  # isinstance(x, SQL)
                self.vars[var.id] = Tag.SQL
            elif self.result_type == Tag.RETURN_SAFE_ARG:  # isinstance(x, int)
                self.vars[var.id] = Tag.SAFE_ARG
            if node.msg is not None:
                self.visit(node.msg)
            return
        self.generic_visit(node)

    # Name resolution

    def _result_type_from_name(self, name):
        if name == 'SQL':
            return Tag.TYPE_SQL
        if name == 'int':  # kept it for f"LIMIT {int(limit)}"
            # TODO remove (tests to adapt if done) - or we could mogrify
            return Tag.RETURN_SAFE_ARG
        return None

    def visit_Name(self, node):
        if node.id == 'cr':
            self.result_type = Tag.CURSOR
        elif node.id in self.vars:
            self.result_type = self.vars[node.id]
        else:
            self.result_type = self._result_type_from_name(node.id)

    def visit_Attribute(self, node):
        self.visit(node.value)
        typ = self.result_type
        if typ is None:
            if node.attr in ('cr', '_cr'):
                # env.cr
                # self._cr
                rt = Tag.CURSOR
            elif node.attr in ('select', 'subselect'):
                # query.select(...)
                rt = Tag.RETURN_SQL
            elif node.attr in ('_table', '_table_sql'):
                # assume these model attributes are safe
                # TODO remove these
                rt = Tag.SAFE_ARG
            else:
                rt = self._result_type_from_name(node.attr)
        elif typ == Tag.TYPE_SQL and node.attr == 'identifier':  # ruff:ignore[if-with-same-arms]
            # SQL.identifier
            rt = Tag.RETURN_SQL
        elif typ == Tag.SQL and node.attr in ('join', 'format'):
            # SQL(',').join(...)
            # (psycopg)  SQL("...").format(...)
            rt = Tag.RETURN_SQL
        elif typ == Tag.CURSOR and node.attr in ('execute', 'executemany', 'execute_values'):
            # cr.execute, etc.
            rt = Tag.EXECUTE_SQL
        else:
            rt = None
        self.result_type = rt

    def _imported(self, prefix, alias: ast.alias):
        name = alias.name
        target = alias.asname or name.partition('.')[0]
        self.vars[target] = None
        if name == 'SQL':
            self.vars[target] = Tag.TYPE_SQL

    def visit_Import(self, node):
        for alias in node.names:
            self._imported('', alias)

    def visit_ImportFrom(self, node):
        if not node.module:
            return self.generic_visit(node)
        for alias in node.names:
            self._imported(node.module, alias)

    # Expressions

    def visit_Constant(self, node):
        self.result_type = Tag.SAFE_ARG if isinstance(node.value, (str, int)) else None

    def visit_TemplateStr(self, node):
        # consider t-string safe by default
        self.generic_visit(node)
        self.result_type = Tag.SAFE_ARG

    def visit_FormattedValue(self, node):
        self.visit(node.value)
        if node.format_spec or node.conversion != -1:
            self.result_type = None

    def visit_JoinedStr(self, node):
        # handles f-strings including only safe-attributes
        self.result_type = None
        probable_type = None
        for value in node.values:
            self.visit(value)
            if not self.result_type:
                return
            if probable_type is None:
                probable_type = self.result_type
            else:
                probable_type = Tag.merge(probable_type, self.result_type)
                if not probable_type:
                    return
        self.result_type = probable_type

    def visit_BinOp(self, node):
        self.visit(node.left)
        ltyp = self.result_type
        if ltyp == Tag.SAFE_ARG and isinstance(node.op, ast.Mod):
            # TODO remove support for formatting like this
            # "abc %s %s" % (..., ...)
            if isinstance(node.right, ast.Tuple):
                for elem in node.right.elts:
                    self.visit(elem)
                    if self.result_type != ltyp:
                        ltyp = None
                        # don't break, continue checking all items
                self.result_type = ltyp
            else:
                self.visit(node.right)
                # keep the result type
            return
        self.visit(node.right)
        self.result_type = None

    # New scopes

    def visit_FunctionDef(self, node):
        self.vars.pushmap()
        self.in_def_function += 1
        self.generic_visit(node)
        self.in_def_function -= 1
        # in_def_function means locally scoped
        if self.vars.get('$return') == Tag.SQL and self.in_def_function:
            ret = Tag.RETURN_SQL
        elif self.vars.get('$return') == Tag.SAFE_ARG and self.in_def_function:
            ret = Tag.RETURN_SAFE_ARG
        else:
            ret = None
        self.vars.popmap()
        self.vars[node.name] = ret
        self.result_type = None

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.vars.pushmap()
        self.generic_visit(node)
        # declare TYPE_SQL for `class SQL` in odoo.tools.sql
        typ = Tag.TYPE_SQL if node.name == 'SQL' else type
        self.vars.popmap()
        self.vars[node.name] = typ
        self.result_type = None

    def visit_Lambda(self, node):
        self.vars.pushmap()
        self.in_def_function += 1
        self.generic_visit(node)
        self.in_def_function -= 1
        self.vars.popmap()
        if self.result_type == Tag.SQL:
            self.result_type = Tag.RETURN_SQL
        elif self.result_type == Tag.SAFE_ARG:
            self.result_type = Tag.RETURN_SAFE_ARG
        else:
            self.result_type = callable

    def visit_arg(self, node):
        self.generic_visit(node)
        # declared argument `cr` is always a cursor
        typ = Tag.CURSOR if node.arg == 'cr' else None
        self.vars[node.arg] = typ

    # Branching

    def visit_For(self, node):
        self.visit(node.iter)
        if isinstance(node.target, ast.Name):
            self._merge_vars({node.target.id: self.result_type})

        self.vars.pushmap()
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.body:  # second loop to find fixpoints
            self.visit(stmt)
        body_vars = self.vars.popmap()

        self.vars.pushmap()
        for stmt in node.orelse:
            self.visit(stmt)
        else_vars = self.vars.popmap()

        self._merge_vars(body_vars, else_vars)

    def visit_AsyncFor(self, node):
        self.visit_For(node)

    def visit_While(self, node):
        self.visit(node.test)

        self.vars.pushmap()
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.body:  # second loop to find fixpoints
            self.visit(stmt)
        body_vars = self.vars.popmap()

        self.vars.pushmap()
        for stmt in node.orelse:
            self.visit(stmt)
        else_vars = self.vars.popmap()

        self._merge_vars(body_vars, else_vars)

    def visit_If(self, node):
        self.visit(node.test)

        self.vars.pushmap()
        for stmt in node.body:
            self.visit(stmt)
        then_vars = self.vars.popmap()

        self.vars.pushmap()
        for stmt in node.orelse:
            self.visit(stmt)
        else_vars = self.vars.popmap()

        self._merge_vars(then_vars, else_vars)

    def visit_With(self, node):
        for item in node.items:
            self.visit(item.context_expr)

            if isinstance(item.optional_vars, ast.Name):
                self.vars[item.optional_vars.id] = self.result_type

        for stmt in node.body:
            self.visit(stmt)

    def visit_AsyncWith(self, node):
        self.visit_With(node)

    def visit_Match(self, node):
        self.visit(node.subject)
        branches = []

        for case in node.cases:
            self.vars.pushmap()

            if case.guard:
                self.visit(case.guard)

            for stmt in case.body:
                self.visit(stmt)

            branches.append(self.vars.popmap())

        self._merge_vars(*branches)

    def visit_Try(self, node):
        branches = []

        for stmt in node.body:
            self.visit(stmt)

        for handler in node.handlers:
            self.vars.pushmap()

            if handler.name and handler.type:
                self.vars[handler.name] = (
                    self.vars.get(handler.type.id)
                    if isinstance(handler.type, ast.Name)
                    else 'exception'  # marker
                )

            for stmt in handler.body:
                self.visit(stmt)
            branches.append(self.vars.popmap())

        self._merge_vars(*branches)

        for stmt in node.orelse:
            self.visit(stmt)

        for stmt in node.finalbody:
            self.visit(stmt)

    def visit_TryStar(self, node):
        self.visit_Try(node)

    def visit_IfExp(self, node):
        self.visit(node.test)
        self.visit(node.body)
        body_var = self.result_type
        self.visit(node.orelse)
        else_var = self.result_type
        self.result_type = Tag.merge(body_var, else_var)

    def visit_nothing(self, node):
        """No action"""
    visit_Pass = visit_Break = visit_Continue = visit_Load = visit_Store = visit_Del = visit_nothing


class TestSqlInjection(LintCase):
    # TODO enable for tests by default
    def test_sql_injection(self, skip_tests=True):
        visitor_linter = SQLInjectionLinter()
        errors = []
        abort_countdown = 5

        def all_files():
            glob = '*.py'
            root_path = config.root_path
            for root, _, fnames in os.walk(root_path):
                fnames = [opj(root, n) for n in fnames]
                fnames = fnmatch.filter(fnames, glob)
                yield from fnames

            other_modules = [m.name for m in Manifest.all_addon_manifests() if not m.path.startswith(root_path)]
            yield from self.iter_module_files(glob, modules=other_modules)

        path_counter = 0
        parsed_count = 0
        path = ''

        def should_parse(source):
            nonlocal parsed_count
            if b'SQL' in source or b'execute' in source:
                parsed_count += 1
                return True
            return False

        def add_error(node):
            if node.lineno in self.noqa_lines(path, noqa='# pylint: disable=sql-injection'):
                return  # ignored error
            code = ast.unparse(node)
            if len(code) > 80:
                code = code[:77] + '...'
            errors.append(f"{path}:{node.lineno} {code!r}")

        visitor_linter.add_error = add_error
        for path_counter, path in enumerate(all_files(), start=1):
            if skip_tests and '/tests/test_' in path:
                continue
            try:
                self.visit_python_file(path, visitor_linter, should_parse=should_parse)
            except Exception:
                _logger.exception("Error processing %s", path)
                abort_countdown -= 1
                if abort_countdown <= 0:
                    errors.append("Aborting too many errors...")
                    break
            if (parsed_count % 100) == 0:
                _logger.debug("linted... %d files (skipped %d)", parsed_count, path_counter - parsed_count)

        _logger.info("Linter parsed %d files of total %d", parsed_count, path_counter)
        if errors:
            errors.insert(0, f"{len(errors)} sql-injection error")
            self.fail("\n- ".join(errors))
