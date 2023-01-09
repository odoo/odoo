import astroid
from pylint import checkers, interfaces


class OdooBaseChecker(checkers.BaseChecker):
    __implements__ = interfaces.IAstroidChecker
    name = 'odoo'

    msgs = {
        'E8503': (
            'Raise inside unlink override.',
            'raise-unlink-override',
            'Raising errors is not allowed inside unlink overrides, '
            'you can create a method and decorate it with '
            '@api.ondelete(at_uninstall=False), only use '
            'at_uninstall=True if you know what you are doing.'
        )
    }

    @staticmethod
    def _inherits_BaseModel(node):
        return any(getattr(n, 'name', False) == 'BaseModel' for n in node.ancestors())

    def visit_raise(self, node):
        parent = node.parent
        while parent:
            if isinstance(parent, astroid.FunctionDef) and parent.name == 'unlink':
                parent = parent.parent
                if isinstance(parent, astroid.ClassDef) and self._inherits_BaseModel(parent):
                    self.add_message('raise-unlink-override', node=node)
                    break
                continue
            parent = parent.parent

def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
