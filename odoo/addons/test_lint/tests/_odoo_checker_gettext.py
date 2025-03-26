import re
from pathlib import Path

import astroid
import pylint.interfaces
from pylint.checkers import BaseChecker

try:
    from pylint.checkers.utils import only_required_for_messages
except ImportError:
    from pylint.checkers.utils import check_messages as only_required_for_messages

# https://docs.python.org/2.6/library/stdtypes.html#string-formatting-operations
PLACEHOLDER_REGEXP = re.compile(r"""
    (?<!%)             # avoid matching escaped %
    %
    [#0\- +]*          # conversion flag
    (?:\d+|\*)?        # minimum field width
    (?:\.(?:\d+|\*))?  # precision
    [hlL]?             # length modifier
    [bcdeEfFgGnorsxX]  # conversion type
""", re.VERBOSE)
REPR_REGEXP = re.compile(r"%(?:\(\w+\))?r")


def parse_version(s):
    # can't use odoo.tools.parse_version because pythonpath is screwed from
    # inside pylint on runbot
    return [s.rjust(3, '0') for s in s.split('.')]


class OdooBaseChecker(BaseChecker):
    if parse_version(pylint.__version__) < parse_version('2.14.0'):
        __implements__ = pylint.interfaces.IAstroidChecker
    name = 'odoo'

    msgs = {
        'E8502': (
            'Bad usage of _, _lt function.',
            'gettext-variable',
            'See https://www.odoo.com/documentation/master/developer/misc/i18n/translations.html#variables'
        ),
        'E8505': (
            'Usage of _, _lt function with multiple unnamed placeholders',
            'gettext-placeholders',
            'Use keyword arguments when you have multiple placeholders',
        ),
        'E8506': (
            'Usage of %r in _, _lt function',
            'gettext-repr',
            'Don\'t use %r to automatically insert quotes in translation strings. Quotes can be different depending on the language: they must be part of the translated string.',
        ),
        'E8507': (
            'Static string passed to %s without gettext call.',
            'missing-gettext',
            'Ensure that all static strings passed to certain constructs are wrapped in a gettext call.',
        ),
    }

    errors_requiring_gettext = ['UserError', 'ValidationError', 'AccessError', 'AccessDenied', 'MissingError']

    @only_required_for_messages('missing-gettext', 'gettext-variable', 'gettext-placeholders', 'gettext-repr')
    def visit_call(self, node):
        file_path = Path(self.linter.current_file).as_posix()
        if "/test_" in file_path or "/tests/" in file_path:
            return

        node_name = ""
        if isinstance(node.func, astroid.Name):
            node_name = node.func.name
        elif isinstance(node.func, astroid.Attribute):
            node_name = node.func.attrname
        if node_name in self.errors_requiring_gettext and len(node.args) > 0:
            first_arg = node.args[0]
            if not is_whitelisted_argument(first_arg):
                self.add_message("missing-gettext", node=node, args=(node_name,))
                return

        if isinstance(node.func, astroid.Name):
            # direct function call to _
            node_name = node.func.name
        elif isinstance(node.func, astroid.Attribute):
            # method call to env._
            node_name = node.func.attrname
        else:
            return
        if node_name not in ("_", "_lt"):
            return
        first_arg = node.args[0] if node.args else None
        if not (isinstance(first_arg, astroid.Const) and isinstance(first_arg.value, str)):
            self.add_message("gettext-variable", node=node)
            return
        if len(PLACEHOLDER_REGEXP.findall(first_arg.value)) >= 2:
            self.add_message("gettext-placeholders", node=node)
        if re.search(REPR_REGEXP, first_arg.value):
            self.add_message("gettext-repr", node=node)


def register(linter):
    linter.register_checker(OdooBaseChecker(linter))


def is_whitelisted_argument(arg):
    if isinstance(arg, (astroid.Name, astroid.Attribute)):
        return True
    if isinstance(arg, astroid.Subscript):  # ex: errors[0]
        return True
    if isinstance(arg, astroid.Call):  # Assumption: any call inside Error call would return a translated string.
        return True
    if isinstance(arg, astroid.IfExp):  # ex: UserError(_("string_1") if condition else _("string_2"))
        return is_whitelisted_argument(arg.body) and is_whitelisted_argument(arg.orelse)
    if isinstance(arg, astroid.BoolOp):  # ex: UserError(_("string_1") and errors[0] or errors_list.get("msg"))
        return all(is_whitelisted_argument(node) for node in arg.values)
    if isinstance(arg, astroid.BinOp):  # ex: UserError(a + b)
        return is_whitelisted_argument(arg.right) or is_whitelisted_argument(arg.left)
    return False
