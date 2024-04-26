import os

import astroid
from pylint import checkers, interfaces

try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages

class OdooBaseChecker(checkers.BaseChecker):
    try: # TODO, remove once pylint minimal version is 3.0.0
        __implements__ = interfaces.IAstroidChecker
        # see https://github.com/pylint-dev/pylint/commit/358264aaf622505f6d2e8bc699618382981a078c
    except AttributeError:
        pass

    name = 'odoo'

    msgs = {
        'E8502': (
            'Bad usage of _, _lt function.',
            'gettext-variable',
            'See https://www.odoo.com/documentation/15.0/developer/misc/i18n/translations.html#variables'
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
