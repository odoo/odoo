import contextlib
import contextvars
import os
from collections import deque
from contextlib import ExitStack
from typing import Optional

import astroid
try:
    from astroid import NodeNG
except ImportError:
    from astroid.node_classes import NodeNG

import pylint.interfaces
from pylint.checkers import BaseChecker, utils
try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages

DFTL_CURSOR_EXPR = [
    'self.env.cr', 'self._cr',  # new api
    'self.cr',  # controllers and test
    'cr',  # old api
]
# <attribute> or <name>.<attribute> or <call>.<attribute>
ATTRIBUTE_WHITELIST = [
    '_table', 'name', 'lang', 'id', 'get_lang.code'
]

FUNCTION_WHITELIST = [
    'create', 'read', 'write', 'browse', 'select', 'get', 'strip', 'items', '_select', '_from', '_where',
    'any', 'join', 'split', 'tuple', 'get_sql', 'search', 'list', 'set', 'next', '_get_query', '_where_calc'
]

func_call = {}
func_called_for_query = []
root_call: contextvars.ContextVar[Optional[astroid.Call]] =\
    contextvars.ContextVar('root_call', default=None)
@contextlib.contextmanager
def push_call(node: astroid.Call):
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
        nodes = deque([node])
        while nodes:
            node = nodes.popleft()
            if isinstance(node, astroid.Return):
                ret.append(node)
            else:
                nodes.extend(node.get_children())
        return ret

    def _is_asserted(self, node): # If there is an assert on the value of the node, it's very likely to be safe
        asserted = deque((assert_.test for assert_ in node.scope().nodes_of_class(astroid.Assert)))
        while asserted:
            n = asserted.popleft()
            if isinstance(n, astroid.Name) and n.name == node.name:
                return True
            else:
                asserted.extend(n.get_children())
        return False

    def _get_attribute_chain(self, node):
        if isinstance(node, astroid.Attribute):
            return self._get_attribute_chain(node.expr) + '.' + node.attrname
        elif isinstance(node, astroid.Name):
            return node.name
        elif isinstance(node, astroid.Call):
            return self._get_attribute_chain(node.func)
        return '' #FIXME

    def _evaluate_function_call(self, node, args_allowed, position):
        name = node.func.attrname if isinstance(node.func, astroid.Attribute) else node.func.name
        if name == node.scope().name:
            return True
        if  name not in func_called_for_query:
            func_called_for_query.append((name, position, root_call.get()))
            cst_args = self.all_const(node.args, args_allowed=args_allowed)
        if  name in func_call:
            for fun in func_call[name]:
                func_call[name].pop(func_call[name].index(fun))
                for returnNode in self._get_return_node(fun):
                    if not self._is_constexpr(returnNode.value, cst_args, position=position):
                        func_call.pop(name)
                        return False
        return True

    def _is_fstring_cst(self, node: astroid.JoinedStr, args_allowed=False, position=None):
        # an fstring is constant if all its FormattedValue are constant, or
        # are access to private attributes (nb: whitelist?)
        return self.all_const((
            node.value for node in node.values
            if isinstance(node, astroid.FormattedValue)
            if not (isinstance(node.value, astroid.Attribute) and node.value.attrname.startswith('_'))
        ),
            args_allowed=args_allowed,
            position=position
        )

    def all_const(self, nodes, args_allowed=False, position=None):
        return all(
            self._is_constexpr(node, args_allowed=args_allowed, position=position)
            for node in nodes
        )

    def _is_constexpr(self, node: NodeNG, args_allowed=False, position=None):
        if isinstance(node, astroid.Const): # astroid.const is always safe
            return True
        elif isinstance(node, (astroid.List, astroid.Set)):
            return self.all_const(node.elts, args_allowed=args_allowed)
        elif isinstance(node, astroid.Tuple):
            if position is None:
                return self.all_const(node.elts, args_allowed=args_allowed)
            else:
                return self._is_constexpr(node.elts[position], args_allowed=args_allowed)
        elif isinstance(node, astroid.Dict):
            return all(
                self._is_constexpr(k, args_allowed=args_allowed) and self._is_constexpr(v, args_allowed=args_allowed)
                for k, v in node.items
            )
        elif isinstance(node, astroid.Starred):
            return self._is_constexpr(node.value, args_allowed=args_allowed, position=position)
        elif isinstance(node, astroid.BinOp): # recusively infer both side of the operation. Failing if either side is not inferable
            left_operand = self._is_constexpr(node.left, args_allowed=args_allowed)
            right_operand = self._is_constexpr(node.right, args_allowed=args_allowed)
            return left_operand and right_operand
        elif isinstance(node, astroid.Name) or isinstance(node, astroid.AssignName): # Variable: find the assignement instruction in the AST and infer its value.
            assignements = node.lookup(node.name)
            assigned_node = []
            for n in assignements[1]: #assignement[0] contains the scope, so assignment[1] contains the assignement nodes
                if isinstance(n.parent, astroid.FunctionDef):
                    assigned_node += [args_allowed]
                elif isinstance(n.parent, astroid.Arguments):
                    assigned_node += [args_allowed]
                elif isinstance(n.parent, astroid.Tuple): # multi assign a,b = (a,b)
                    statement = n.statement()
                    if isinstance(statement, astroid.For):
                        assigned_node += [self._is_constexpr(statement.iter, args_allowed=args_allowed)]
                    elif isinstance(statement, astroid.Assign):
                        assigned_node += [self._is_constexpr(statement.value, args_allowed=args_allowed, position=n.parent.elts.index(n))]
                    else:
                        raise TypeError(f"Expected statement Assign or For, got {statement}")
                elif isinstance(n.parent, astroid.For):
                    assigned_node.append(self._is_constexpr(n.parent.iter, args_allowed=args_allowed))
                elif isinstance(n.parent, astroid.AugAssign):
                    left = self._is_constexpr(n.parent.target, args_allowed=args_allowed)
                    right = self._is_constexpr(n.parent.value, args_allowed=args_allowed)
                    assigned_node.append(left and right)
                elif isinstance(n.parent, astroid.Module):
                    return True
                else:
                    assigned_node += [self._is_constexpr(n.parent.value, args_allowed=args_allowed)]
            if assigned_node and all(assigned_node):
                return True
            return self._is_asserted(node)
        elif isinstance(node, astroid.JoinedStr):
            return self._is_fstring_cst(node, args_allowed)
        elif isinstance(node, astroid.Call):
            if isinstance(node.func, astroid.Attribute):
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
        elif isinstance(node, astroid.IfExp):
            body = self._is_constexpr(node.body, args_allowed=args_allowed)
            orelse = self._is_constexpr(node.orelse, args_allowed=args_allowed)
            return body and orelse
        elif isinstance(node, astroid.Subscript):
            return self._is_constexpr(node.value, args_allowed=args_allowed)
        elif isinstance(node, astroid.BoolOp):
            return self.all_const(node.values, args_allowed=args_allowed)

        elif isinstance(node, astroid.Attribute):
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
        while isinstance(node_expr, astroid.Attribute):
            expr_list.insert(0, node_expr.attrname)
            node_expr = node_expr.expr
        if isinstance(node_expr, astroid.Name):
            expr_list.insert(0, node_expr.name)
        cursor_name = '.'.join(expr_list)
        return cursor_name

    def _allowable(self, node):
        """
        :type node: NodeNG
        """
        scope = node.scope()
        if isinstance(scope, astroid.FunctionDef) and (scope.name.startswith("_") or scope.name == 'init'):
            return True

        infered = utils.safe_infer(node)
        # The package 'psycopg2' must be installed to infer
        # ignore sql.SQL().format or variable that can be infered as constant
        if infered and infered.pytype().startswith('psycopg2'):
            return True
        if self._is_constexpr(node):  # If we can infer the value at compile time, it cannot be injected
            return True

        if isinstance(node, astroid.Call):
            node = node.func
        # self._thing is OK (mostly self._table), self._thing() also because
        # it's a common pattern of reports (self._select, self._group_by, ...)
        return (isinstance(node, astroid.Attribute)
            and isinstance(node.expr, astroid.Name)
            and node.attrname.startswith('_')
        )

    def _check_concatenation(self, node):
        node = self.resolve(node)

        if self._allowable(node):
            return False

        if isinstance(node, astroid.BinOp) and node.op in ('%', '+'):
            if isinstance(node.right, astroid.Tuple):
                # execute("..." % (self._table, thing))
                if not all(map(self._allowable, node.right.elts)):
                    return True
            elif isinstance(node.right, astroid.Dict):
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
        if isinstance(node, astroid.Call) \
                and isinstance(node.func, astroid.Attribute) \
                and node.func.attrname == 'format':

            return not (
                    all(map(self._allowable, node.args or []))
                and all(self._allowable(keyword.value) for keyword in (node.keywords or []))
            )

        # check execute(f'foo {...}')
        if isinstance(node, astroid.JoinedStr):
            return not all(
                self._allowable(formatted.value)
                for formatted in node.nodes_of_class(astroid.FormattedValue)
            )

    def resolve(self, node):
        # if node is a variable, find how it was built
        if isinstance(node, astroid.Name):
            for target in node.lookup(node.name)[1]:
                # could also be e.g. arguments (if the source is a function parameter)
                if isinstance(target.parent, astroid.Assign):
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
            isinstance(node, astroid.Call) and node.args and
            isinstance(node.func, astroid.Attribute) and
            node.func.attrname in ('execute', 'executemany') and
            # cursor expr (see above)
            self._get_cursor_name(node.func) in DFTL_CURSOR_EXPR and
            # ignore in test files, probably not accessible
            not current_file_bname.startswith('test_')
        ):
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

        if node.name.startswith('__') or node.name in FUNCTION_WHITELIST:
            return

        nodes = func_call.setdefault(node.name, [])
        if node not in nodes:
            nodes.append(node)

        mapped_func_called_for_query = [x[0] for x in func_called_for_query]
        if node.name not in mapped_func_called_for_query:
            return

        index = mapped_func_called_for_query.index(node.name)
        _, position, call = func_called_for_query.pop(index)
        if not all(
            self._is_constexpr(return_node.value, position=position)
            for return_node in self._get_return_node(node)
        ):
            self.add_message('sql-injection', node=node, args='because it is used to build a query in file %(file)s:%(line)s'% {'file': self._infer_filename(call), 'line':str(call.lineno)})

def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
