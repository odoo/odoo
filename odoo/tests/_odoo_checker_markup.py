from typing import Optional

import astroid
from pylint import interfaces, checkers

try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages


class OdooBaseChecker(checkers.BaseChecker):
    try:  # TODO, remove once pylint minimal version is 3.0.0
        __implements__ = interfaces.IAstroidChecker
        # see https://github.com/pylint-dev/pylint/commit/358264aaf622505f6d2e8bc699618382981a078c
    except AttributeError:
        pass
    name = 'odoo'

    msgs = {
        'E8504': (
            'The Markup constructor called with a non-constant argument',
            'non-const-markup',
            '',
        )
    }

    @only_required_for_messages('non-const-markup')
    def visit_call(self, node):
        if (isinstance(node.func, astroid.Name) and
                node.func.name == "Markup" and
                not self._is_constant(node.args[0])):
            self.add_message('non-const-markup', node=node, col_offset=len(node.as_string().split('\\n')))
        elif (isinstance(node.func, astroid.Attribute) and
                node.func.attrname == "Markup" and
                not self._is_constant(node.args[0])):
            self.add_message('non-const-markup', node=node, col_offset=len(node.as_string().split('\\n')))

    def _is_constant(self, node: Optional[astroid.node_classes.NodeNG]) -> bool:
        if isinstance(node, astroid.Const) or node is None:
            return True
        elif isinstance(node, astroid.JoinedStr):
            return all(map(self._is_constant, node.values))
        elif isinstance(node, astroid.FormattedValue):
            return self._is_constant(node.value)
        elif isinstance(node, astroid.Name):
            _, assignments = node.lookup(node.name)
            return all(map(self._is_constant, assignments))
        elif isinstance(node, astroid.AssignName):
            return self._is_constant(node.parent)
        elif isinstance(node, astroid.Assign):
            return self._is_constant(node.value)
        elif (isinstance(node, astroid.Call) and
              isinstance(node.func, astroid.Attribute) and
              node.func.attrname in ["format", "join"]):
            return (self._is_constant(node.func.expr) and
                    all(map(self._is_constant, node.args)) and
                    all(map(self._is_constant, node.keywords)))
        elif isinstance(node, astroid.Keyword):
            return self._is_constant(node.value)
        elif isinstance(node, (astroid.List, astroid.Set, astroid.Tuple)):
            return all(map(self._is_constant, node.elts))
        elif isinstance(node, astroid.Dict):
            return all(map(self._is_constant, node.values))
        elif isinstance(node, astroid.BinOp):
            return self._is_constant(node.left) and self._is_constant(node.right)
        elif isinstance(node, astroid.IfExp):
            return self._is_constant(node.body) and self._is_constant(node.orelse)
        return False

def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
