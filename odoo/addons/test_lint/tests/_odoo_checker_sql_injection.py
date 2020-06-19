import os

import astroid
from pylint import checkers, interfaces

DFTL_CURSOR_EXPR = [
    'self.env.cr', 'self._cr',  # new api
    'self.cr',  # controllers and test
    'cr',  # old api
]


class OdooBaseChecker(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker
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

    def _get_func_name(self, node):
        func_name = (
            isinstance(node, astroid.Name) and node.name or
            isinstance(node, astroid.Attribute) and node.attrname or '')
        return func_name

    def _check_concatenation(self, node):
        is_bin_op = False
        if isinstance(node, astroid.BinOp) and node.op in ('%', '+'):
            # execute("..." % self._table)
            if (isinstance(node.right, astroid.Attribute) and
                    not node.right.attrname.startswith('_')):
                is_bin_op = True
            if isinstance(node.right, astroid.Tuple):
                for elt in node.right.elts:
                    if (isinstance(elt, astroid.Call) and
                            # Ignoring for this case: execute("..." % _foo(...))
                            not self._get_func_name(elt.func).startswith('_')):
                        is_bin_op = True

        is_format = False
        # execute("...".format(self._table, table=self._table))
        if (isinstance(node, astroid.Call) and
                self._get_func_name(node.func) == 'format'):
            for keyword in node.keywords or []:
                if (isinstance(keyword.value, astroid.Attribute) and
                        not keyword.value.attrname.startswith('_')):
                    is_format = True
                    break
            for argument in node.args or []:
                if (isinstance(argument, astroid.Name) and not argument.name.startswith('_')):
                    is_format = True
                    break

        return is_bin_op or is_format

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
        # if first parameter is a variable, check how it was built instead
        if (not is_concatenation and isinstance(first_arg, (astroid.Name, astroid.Subscript))):

            # 1) look for parent scope (where the definition lives)
            current = node
            while (current and not isinstance(current.parent, astroid.FunctionDef)):
                current = current.parent
            parent = current.parent

            # 2) check how was the variable built
            for node_ofc in parent.nodes_of_class(astroid.Assign):
                if node_ofc.targets[0].as_string() != first_arg.as_string():
                    continue
                is_concatenation = self._check_concatenation(node_ofc.value)
                if is_concatenation:
                    break
        return is_concatenation

    @checkers.utils.check_messages('sql-injection')
    def visit_call(self, node):
        if self._check_sql_injection_risky(node):
            self.add_message('sql-injection', node=node)


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
