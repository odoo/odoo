from typing import Optional

import astroid
from pylint import interfaces, checkers

try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages


class OdooBaseChecker(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker
    name = 'odoo'

    msgs = {
        'E8504': (
            'The Markup constructor has been called with a non-constant argument.',
            'non-const-markup',
            'The argument of the Markup constructor must be a constant to prevent XSS attacks.',
        )
    }

    @only_required_for_messages('non-const-markup')
    def visit_call(self, node):
        if (isinstance(node.func, astroid.Name) and
                node.func.name == "Markup" and
                not all(map(self._is_constant, node.args))):
            self.add_message('non-const-markup', node=node)

    def _is_constant(self, node: Optional[astroid.node_classes.NodeNG]) -> bool:
        if isinstance(node, astroid.Const) or node is None:
            return True
        elif isinstance(node, astroid.JoinedStr):
            return all(map(self._is_constant, node.values))
        elif isinstance(node, astroid.FormattedValue):
            return self._is_constant(node.value)
        elif isinstance(node, astroid.Name):
            _, assignments = node.lookup(node.name)
            if not assignments:
                return False
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
            return all(map(lambda item: self._is_constant(item[0]) and self._is_constant(item[1]), node.items))
        elif isinstance(node, astroid.BinOp):
            return self._is_constant(node.left) and self._is_constant(node.right)
        elif isinstance(node, astroid.IfExp):
            return self._is_constant(node.body) and self._is_constant(node.orelse)
        return False


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
