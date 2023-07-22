import astroid
from pylint.checkers import BaseChecker
try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages

class OdooBaseChecker(BaseChecker):
    name = 'odoo'

    msgs = {
        'E8502': (
            'Bad usage of _, _lt function.',
            'gettext-variable',
            'See https://www.odoo.com/documentation/saas-16.4/developer/misc/i18n/translations.html#variables'
        )
    }

    @only_required_for_messages('gettext-variable')
    def visit_call(self, node):
        if isinstance(node.func, astroid.Name) and node.func.name in ('_', '_lt'):
            first_arg = node.args[0]
            if not (isinstance(first_arg, astroid.Const) and isinstance(first_arg.value, str)):
                self.add_message('gettext-variable', node=node)


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))
