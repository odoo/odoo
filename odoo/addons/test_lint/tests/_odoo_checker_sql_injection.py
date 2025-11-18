import collections
import contextlib
import contextvars
import functools
import os
from collections import deque
from contextlib import ExitStack
from typing import Optional

from astroid import nodes

import pylint.interfaces
from pylint.checkers import BaseChecker, utils
try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages

DFTL_CURSOR_EXPR = [
    'self.env.cr', 'self.env.cr',  # new api
    'self.cr',  # controllers and test
    'cr',  # old api
    'odoo.tools',
    'tools',
]
# <attribute> or <name>.<attribute> or <call>.<attribute>
ATTRIBUTE_WHITELIST = [
    '_table', 'name', 'lang', 'id', 'get_lang.code'
]

FUNCTION_WHITELIST = {
    'create', 'read', 'write', 'browse', 'select', 'get', 'strip', 'items', '_select', '_from', '_where',
    'any', 'join', 'split', 'tuple', 'get_sql', 'search', 'list', 'set', 'next', 'SQL'
}

function_definitions = collections.defaultdict(list)
callsites_for_queries = collections.defaultdict(list)
root_call: contextvars.ContextVar[Optional[nodes.Call]] =\
    contextvars.ContextVar('root_call', default=None)
@contextlib.contextmanager
def push_call(node: nodes.Call):
    with ExitStack() as s:
        if root_call.get() is None:
            t = root_call.set(node)
            s.callback(root_call.reset, t)
        yield

def parse_version(s):
    # can't use odoo.tools.parse_version because pythonpath is screwed from
    # inside pylint on runbot
    return [s.rjust(3, '0') for s in s.split('.')]

class OdooBaseChecker(BaseChecker):
    # `test_printf` fails if this is not set in 2.5 (???), but it's deprecated
    # in 2.14, so make conditional
    if parse_version(pylint.__version__) < parse_version('2.14.0'):
        __implements__ = pylint.interfaces.IAstroidChecker
    name = 'odoo'

    msgs = {
        'E8501': (
            'Possible SQL injection risk %s.',
            'sql-injection',
            'See http://www.bobby-tables.com try using '
            'execute(query, tuple(params))',
        )
    }

    def _infer_filename(self, node):
        while 'file' not in dir(node):
            node = node.parent
        return node.file
    def _get_return_node(self, node):
        ret = []
        q = deque([node])
        while q:
            node = q.popleft()
            if isinstance(node, nodes.Return):
                ret.append(node)
            else:
                q.extend(node.get_children())
        return ret

    def _is_asserted(self, node): # If there is an assert on the value of the node, it's very likely to be safe
        asserted = deque(assert_.test for assert_ in node.scope().nodes_of_class(nodes.Assert))
        while asserted:
            n = asserted.popleft()
            if isinstance(n, nodes.Name) and n.name == node.name:
                return True
            else:
                asserted.extend(n.get_children())
        return False

    def _get_attribute_chain(self, node):
        if isinstance(node, nodes.Attribute):
            return self._get_attribute_chain(node.expr) + '.' + node.attrname
        elif isinstance(node, nodes.Name):
            return node.name
        elif isinstance(node, nodes.Call):
            return self._get_attribute_chain(node.func)
        return '' #FIXME

    def _evaluate_function_call(self, node, args_allowed, position):
        name = node.func.attrname if isinstance(node.func, nodes.Attribute) else node.func.name
        if name == 'SQL':
            return True
        if isinstance(node.scope(), nodes.GeneratorExp):
            return True
        if name == node.scope().name:
            return True

        const_args = self.all_const(node.args, args_allowed=args_allowed)
        # store callsite in case the function is not define yet
        callsites_for_queries[name].append((position, const_args, root_call.get()))
        # evaluate known defs for callsite
        if funs := function_definitions[name]:
            return all(
                self._is_const_def(fun, const_args=const_args, position=position)
                for fun in funs
            )
        return True

    def _is_fstring_cst(self, node: nodes.JoinedStr, args_allowed=False, position=None):
        # an fstring is constant if all its FormattedValue are constant, or
        # are access to private attributes (nb: whitelist?)
        return self.all_const((
            node.value for node in node.values
            if isinstance(node, nodes.FormattedValue)
            if not (isinstance(node.value, nodes.Attribute) and node.value.attrname.startswith('_'))
        ),
            args_allowed=args_allowed,
            position=position
        )

    def all_const(self, nodes, args_allowed=False, position=None):
        return all(
            self._is_constexpr(node, args_allowed=args_allowed, position=position)
            for node in nodes
        )

    def _is_constexpr(self, node: nodes.NodeNG, *, args_allowed=False, position=None):
        if isinstance(node, nodes.Const):  # astroid.const is always safe
            return True
        elif isinstance(node, (nodes.List, nodes.Set)):
            return self.all_const(node.elts, args_allowed=args_allowed)
        elif isinstance(node, nodes.Tuple):
            if position is None:
                return self.all_const(node.elts, args_allowed=args_allowed)
            else:
                return self._is_constexpr(node.elts[position], args_allowed=args_allowed)
        elif isinstance(node, nodes.Dict):
            return all(
                self._is_constexpr(k, args_allowed=args_allowed) and self._is_constexpr(v, args_allowed=args_allowed)
                for k, v in node.items
            )
        elif isinstance(node, nodes.Starred):
            return self._is_constexpr(node.value, args_allowed=args_allowed, position=position)
        elif isinstance(node, nodes.BinOp):  # recusively infer both side of the operation. Failing if either side is not inferable
            left_operand = self._is_constexpr(node.left, args_allowed=args_allowed)
            # This case allows to always consider a string formatted with %d to be safe
            if node.op == '%' and \
                isinstance(node.left, nodes.Const) and \
                node.left.pytype() == 'builtins.str' and \
                '%d' in node.left.value and \
                not '%s' in node.left.value:
                return True
            right_operand = self._is_constexpr(node.right, args_allowed=args_allowed)
            return left_operand and right_operand
        elif isinstance(node, (nodes.Name, nodes.AssignName)):  # Variable: find the assignement instruction in the AST and infer its value.
            assignment = node.lookup(node.name)
            assigned_node = []
            for n in assignment[1]:  # assignment[0] contains the scope, so assignment[1] contains the assignement nodes
                # FIXME: makes no sense, assuming this gets
                #        `visit_functiondef`'d we should just ignore it
                if isinstance(n.parent, (nodes.FunctionDef, nodes.Arguments)):
                    assigned_node += [args_allowed]
                elif isinstance(n.parent, nodes.Tuple):  # multi assign a,b = (a,b)
                    statement = n.statement()
                    if isinstance(statement, nodes.For):
                        assigned_node += [self._is_constexpr(statement.iter, args_allowed=args_allowed)]
                    elif isinstance(statement, nodes.Assign):
                        assigned_node += [self._is_constexpr(statement.value, args_allowed=args_allowed, position=n.parent.elts.index(n))]
                    else:
                        raise TypeError(f"Expected statement Assign or For, got {statement}")
                elif isinstance(n.parent, nodes.For):
                    assigned_node.append(self._is_constexpr(n.parent.iter, args_allowed=args_allowed))
                elif isinstance(n.parent, nodes.AugAssign):
                    left = self._is_constexpr(n.parent.target, args_allowed=args_allowed)
                    right = self._is_constexpr(n.parent.value, args_allowed=args_allowed)
                    assigned_node.append(left and right)
                elif isinstance(n.parent, nodes.Module):
                    return True
                else:
                    if isinstance(n.parent, nodes.Comprehension):
                        assigned_node += [self._is_constexpr(n.parent.iter, args_allowed=args_allowed)]
                    else:
                        assigned_node += [self._is_constexpr(n.parent.value, args_allowed=args_allowed)]
            if assigned_node and all(assigned_node):
                return True
            return self._is_asserted(node)
        elif isinstance(node, nodes.JoinedStr):
            return self._is_fstring_cst(node, args_allowed)
        elif isinstance(node, nodes.Call):
            if isinstance(node.func, nodes.Attribute):
                if node.func.attrname == 'append':
                    return self._is_constexpr(node.args[0])
                elif node.func.attrname == 'format':
                    return (
                        self._is_constexpr(node.func.expr, args_allowed=args_allowed)
                    and self.all_const(node.args, args_allowed=args_allowed)
                    and self.all_const((key.value for key in node.keywords or []), args_allowed=args_allowed)
                    )
            with push_call(node):
                return self._evaluate_function_call(node, args_allowed=args_allowed, position=position)
        elif isinstance(node, nodes.IfExp):
            body = self._is_constexpr(node.body, args_allowed=args_allowed)
            orelse = self._is_constexpr(node.orelse, args_allowed=args_allowed)
            return body and orelse
        elif isinstance(node, nodes.Subscript):
            return self._is_constexpr(node.value, args_allowed=args_allowed)
        elif isinstance(node, nodes.BoolOp):
            return self.all_const(node.values, args_allowed=args_allowed)

        elif isinstance(node, nodes.Attribute):
            attr_chain = self._get_attribute_chain(node)
            while attr_chain:
                if attr_chain in ATTRIBUTE_WHITELIST or attr_chain.startswith('_'):
                    return True
                if '.' in attr_chain:
                    _, attr_chain = attr_chain.split('.', 1)
                else:
                    break
            return False
        return False

    def _get_cursor_name(self, node):
        expr_list = []
        node_expr = node.expr
        while isinstance(node_expr, nodes.Attribute):
            expr_list.insert(0, node_expr.attrname)
            node_expr = node_expr.expr
        if isinstance(node_expr, nodes.Name):
            expr_list.insert(0, node_expr.name)
        cursor_name = '.'.join(expr_list)
        return cursor_name

    def _allowable(self, node: nodes.NodeNG) -> bool:
        scope = node.scope()
        if isinstance(scope, nodes.FunctionDef) and (scope.name.startswith("_") or scope.name == 'init'):
            return True

        infered = utils.safe_infer(node)
        # The package 'psycopg2' must be installed to infer
        # ignore sql.SQL().format or variable that can be infered as constant
        if infered and infered.pytype().startswith('psycopg2'):
            return True
        if self._is_constexpr(node):  # If we can infer the value at compile time, it cannot be injected
            return True

        # self._thing is OK (mostly self._table), self._thing() also because
        # it's a common pattern of reports (self._select, self._group_by, ...)
        return (isinstance(node, nodes.Attribute)
            and isinstance(node.expr, nodes.Name)
            and node.attrname.startswith('_')
        )

    def _check_concatenation(self, node: nodes.NodeNG) -> bool | None:
        node = self.resolve(node)

        if self._allowable(node):
            return False

        if isinstance(node, nodes.BinOp) and node.op in ('%', '+'):
            if isinstance(node.right, nodes.Tuple):
                # execute("..." % (self._table, thing))
                if not all(map(self._allowable, node.right.elts)):
                    return True
            elif isinstance(node.right, nodes.Dict):
                # execute("..." % {'table': self._table}
                if not all(self._allowable(v) for _, v in node.right.items):
                    return True
            elif not self._allowable(node.right):
                # execute("..." % self._table)
                return True
            # Consider cr.execute('SELECT ' + operator + ' FROM table' + 'WHERE')"
            # node.repr_tree()
            # BinOp(
            #    op='+',
            #    left=BinOp(
            #       op='+',
            #       left=BinOp(
            #          op='+',
            #          left=Const(value='SELECT '),
            #          right=Name(name='operator')),
            #       right=Const(value=' FROM table')),
            #    right=Const(value='WHERE'))
            # Notice that left node is another BinOp node
            return self._check_concatenation(node.left)

        # check execute("...".format(self._table, table=self._table))
        if isinstance(node, nodes.Call) \
                and isinstance(node.func, nodes.Attribute) \
                and node.func.attrname == 'format':

            return not (
                    all(map(self._allowable, node.args or []))
                and all(self._allowable(keyword.value) for keyword in (node.keywords or []))
            )

        # check execute(f'foo {...}')
        if isinstance(node, nodes.JoinedStr):
            return not all(
                self._allowable(formatted.value)
                for formatted in node.nodes_of_class(nodes.FormattedValue)
            )

        return None

    def resolve(self, node):
        # if node is a variable, find how it was built
        if isinstance(node, nodes.Name):
            for target in node.lookup(node.name)[1]:
                # could also be e.g. arguments (if the source is a function parameter)
                if isinstance(target.parent, nodes.Assign):
                    # FIXME: handle multiple results (e.g. conditional assignment)
                    return target.parent.value
        # otherwise just return the original node for checking
        return node

    def _check_sql_injection_risky(self, node):
        # Inspired from OCA/pylint-odoo project
        # Thanks @moylop260 (Moisés López) & @nilshamerlinck (Nils Hamerlinck)
        current_file_bname = os.path.basename(self.linter.current_file)
        if not (
            # .execute() or .executemany()
            isinstance(node, nodes.Call) and node.args and
            ((isinstance(node.func, nodes.Attribute) and node.func.attrname in ('execute', 'executemany', 'SQL') and self._get_cursor_name(node.func) in DFTL_CURSOR_EXPR) or
            (isinstance(node.func, nodes.Name) and node.func.name == 'SQL')) and
            # ignore in test files, probably not accessible
            not current_file_bname.startswith('test_')
        ):
            return False
        if len(node.args) == 0:
            return False
        first_arg = node.args[0]
        is_concatenation = self._check_concatenation(first_arg)
        if is_concatenation is not None:
            return is_concatenation
        return True

    @only_required_for_messages('sql-injection')
    def visit_call(self, node):
        if not self.linter.is_message_enabled('E8501', node.lineno):
            return
        if self._check_sql_injection_risky(node):
            self.add_message('sql-injection', node=node, args='')

    @only_required_for_messages('sql-injection')
    def visit_functiondef(self, node):
        if not self.linter.is_message_enabled('E8501', node.lineno):
            return
        if os.path.basename(self.linter.current_file).startswith('test_'):
            return

        # store def for future callsites
        function_definitions[node.name].append(node)

        # evaluate previously seen callsites
        # TODO: group by (position, const_args), if any None check that, otherwise check individual positions
        for p, a, call in callsites_for_queries[node.name]:
            if not self._is_const_def(node, const_args=a, position=p):
                self.add_message(
                    'sql-injection',
                    node=node,
                    args='because it is used to build a query in file %(file)s:%(line)s' % {
                        'file': self._infer_filename(call),
                        'line': str(call.lineno)
                    }
                )

    @functools.lru_cache(None)
    def _is_const_def(self, node: nodes.FunctionDef, /, *, position: Optional[int], const_args: bool = False) -> bool:
        if node.name.startswith('__') or node.name in FUNCTION_WHITELIST:
            return True

        return all(
            self._is_constexpr(return_node.value, args_allowed=const_args, position=position)
            for return_node in self._get_return_node(node)
        )


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
