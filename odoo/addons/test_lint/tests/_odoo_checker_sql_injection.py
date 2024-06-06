import contextlib
import os

import astroid
from pylint import checkers, interfaces

try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages


DFTL_CURSOR_EXPR = [
    'self.env.cr', 'self._cr',  # new api
    'self.cr',  # controllers and test
    'cr',  # old api
]


class OdooBaseChecker(checkers.BaseChecker):
    with contextlib.suppress(AttributeError):  # TODO, remove once pylint minimal version is 3.0.0
        __implements__ = interfaces.IAstroidChecker
        # see https://github.com/pylint-dev/pylint/commit/358264aaf622505f6d2e8bc699618382981a078c

    name = 'odoo'

    msgs = {
        'E8501': (
            'Possible SQL injection risk.',
            'sql-injection',
            'See http://www.bobby-tables.com try using '
            'execute(query, tuple(params))',
        )
    }

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
        infered = checkers.utils.safe_infer(node)
        # The package 'psycopg2' must be installed to infer
        # ignore sql.SQL().format
        if infered and infered.pytype().startswith('psycopg2'):
            return True
        if isinstance(node, astroid.Call):
            node = node.func
        # self._thing is OK (mostly self._table), self._thing() also because
        # it's a common pattern of reports (self._select, self._group_by, ...)
        return (isinstance(node, astroid.Attribute)
            and isinstance(node.expr, astroid.Name)
            and node.attrname.startswith('_')
            # cr.execute('SELECT * FROM %s' % 'table') is OK since that is a constant
            or isinstance(node, astroid.Const)
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
            # cr.execute("select * from %s" % foo, [bar]) -> probably a good reason for string formatting
            len(node.args) <= 1 and
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
        if self._check_sql_injection_risky(node):
            self.add_message('sql-injection', node=node)


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
