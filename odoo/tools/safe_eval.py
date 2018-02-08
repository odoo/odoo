# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
safe_eval module - methods intended to provide more restricted alternatives to
                   evaluate simple and/or untrusted code.

Methods in this module are typically used as alternatives to eval() to parse
OpenERP domain strings, conditions and expressions, mostly based on locals
condition/math builtins.
"""

# Module partially ripped from/inspired by several different sources:
#  - http://code.activestate.com/recipes/286134/
#  - safe_eval in lp:~xrg/openobject-server/optimize-5.0
#  - safe_eval in tryton http://hg.tryton.org/hgwebdir.cgi/trytond/rev/bbb5f73319ad
import dis
from opcode import HAVE_ARGUMENT, opmap, opname

import functools
from psycopg2 import OperationalError
from types import CodeType
import logging
import sys
import werkzeug

from . import pycompat
from .misc import ustr
from . import pycompat

import odoo

unsafe_eval = eval

__all__ = ['test_expr', 'safe_eval', 'const_eval']

# The time module is usually already provided in the safe_eval environment
# but some code, e.g. datetime.datetime.now() (Windows/Python 2.5.2, bug
# lp:703841), does import time.
_ALLOWED_MODULES = ['_strptime', 'math', 'time']

_UNSAFE_ATTRIBUTES = ['f_builtins', 'f_globals', 'f_locals', 'gi_frame',
                      'co_code', 'func_globals']
_POSSIBLE_OPCODES_P3 = [
    # opcodes for `with` statement cleanup process
    'WITH_CLEANUP_START', 'WITH_CLEANUP_FINISH',
    # f-strings
    'FORMAT_VALUE', 'BUILD_STRING',
    # extended iterable unpacking: LHS has * e.g. `a, *b, c = thing()`
    'UNPACK_EX',
    # collection literals with unpacking e.g. [*a, *b]
    'BUILD_LIST_UNPACK', 'BUILD_TUPLE_UNPACK', 'BUILD_SET_UNPACK', 'BUILD_MAP_UNPACK',
    # packs args/kwargs for calls with multiple unpacks e.g. foo(*a, *b, *c)
    'BUILD_TUPLE_UNPACK_WITH_CALL', 'BUILD_MAP_UNPACK_WITH_CALL',
    # ???
    'GET_YIELD_FROM_ITER',
    # matrix operator
    'BINARY_MATRIX_MULTIPLY', 'INPLACE_MATRIX_MULTIPLY',
]

# opcodes necessary to build literal values
_CONST_OPCODES = set(opmap[x] for x in [
    # stack manipulations
    'POP_TOP', 'ROT_TWO', 'ROT_THREE', 'ROT_FOUR', 'DUP_TOP', 'DUP_TOPX',
    'DUP_TOP_TWO',  # replaces DUP_TOPX in P3
    'LOAD_CONST',
    'RETURN_VALUE', # return the result of the literal/expr evaluation
    # literal collections
    'BUILD_LIST', 'BUILD_MAP', 'BUILD_TUPLE', 'BUILD_SET',
    # 3.6: literal map with constant keys https://bugs.python.org/issue27140
    'BUILD_CONST_KEY_MAP',
    # until Python 3.5, literal maps are compiled to creating an empty map
    # (pre-sized) then filling it key by key
    'STORE_MAP',
] if x in opmap)

# operations on literal values
_EXPR_OPCODES = _CONST_OPCODES.union(set(opmap[x] for x in [
    'UNARY_POSITIVE', 'UNARY_NEGATIVE', 'UNARY_NOT',
    'UNARY_INVERT', 'BINARY_POWER', 'BINARY_MULTIPLY',
    'BINARY_DIVIDE', 'BINARY_FLOOR_DIVIDE', 'BINARY_TRUE_DIVIDE',
    'BINARY_MODULO', 'BINARY_ADD', 'BINARY_SUBTRACT', 'BINARY_SUBSCR',
    'BINARY_LSHIFT', 'BINARY_RSHIFT', 'BINARY_AND', 'BINARY_XOR',
    'BINARY_OR', 'INPLACE_ADD', 'INPLACE_SUBTRACT', 'INPLACE_MULTIPLY',
    'INPLACE_DIVIDE', 'INPLACE_REMAINDER', 'INPLACE_POWER',
    'INPLACE_LEFTSHIFT', 'INPLACE_RIGHTSHIFT', 'INPLACE_AND',
    'INPLACE_XOR','INPLACE_OR', 'STORE_SUBSCR',
    # slice operations (Python 3 only has BUILD_SLICE)
    'SLICE+0', 'SLICE+1', 'SLICE+2', 'SLICE+3', 'BUILD_SLICE',
    # comprehensions
    'LIST_APPEND', 'MAP_ADD', 'SET_ADD',
    'COMPARE_OP',
] if x in opmap))

_SAFE_OPCODES = _EXPR_OPCODES.union(set(opmap[x] for x in [
    'POP_BLOCK', 'POP_EXCEPT', # Seems to be a special-case of POP_BLOCK for P3
    'SETUP_LOOP', 'BREAK_LOOP', 'CONTINUE_LOOP',
    'MAKE_FUNCTION', 'CALL_FUNCTION',
    'EXTENDED_ARG',  # P3.6 for long jump offsets.
    # P3: https://bugs.python.org/issue27213
    'CALL_FUNCTION_EX',
    # Already in P2 but apparently the first one is used more aggressively in P3
    'CALL_FUNCTION_KW', 'CALL_FUNCTION_VAR', 'CALL_FUNCTION_VAR_KW',
    'GET_ITER', 'FOR_ITER', 'YIELD_VALUE',
    'JUMP_FORWARD', 'JUMP_IF_TRUE', 'JUMP_IF_FALSE', 'JUMP_ABSOLUTE',
    # New in Python 2.7 - http://bugs.python.org/issue4715 :
    'JUMP_IF_FALSE_OR_POP', 'JUMP_IF_TRUE_OR_POP', 'POP_JUMP_IF_FALSE',
    'POP_JUMP_IF_TRUE', 'SETUP_EXCEPT', 'END_FINALLY', 'RAISE_VARARGS',
    'LOAD_NAME', 'STORE_NAME', 'DELETE_NAME', 'LOAD_ATTR',
    'LOAD_FAST', 'STORE_FAST', 'DELETE_FAST', 'UNPACK_SEQUENCE',
    'LOAD_GLOBAL', # Only allows access to restricted globals
] if x in opmap))

_logger = logging.getLogger(__name__)

if hasattr(dis, 'get_instructions'):
    def _get_opcodes(codeobj):
        """_get_opcodes(codeobj) -> [opcodes]

        Extract the actual opcodes as an iterator from a code object

        >>> c = compile("[1 + 2, (1,2)]", "", "eval")
        >>> list(_get_opcodes(c))
        [100, 100, 23, 100, 100, 102, 103, 83]
        """
        return (i.opcode for i in dis.get_instructions(codeobj))
else:
    def _get_opcodes(codeobj):
        i = 0
        byte_codes = codeobj.co_code
        while i < len(byte_codes):
            code = ord(byte_codes[i:i+1])
            yield code

            if code >= HAVE_ARGUMENT:
                i += 3
            else:
                i += 1

def assert_no_dunder_name(code_obj, expr):
    """ assert_no_dunder_name(code_obj, expr) -> None

    Asserts that the code object does not refer to any "dunder name"
    (__$name__), so that safe_eval prevents access to any internal-ish Python
    attribute or method (both are loaded via LOAD_ATTR which uses a name, not a
    const or a var).

    Checks that no such name exists in the provided code object (co_names).

    :param code_obj: code object to name-validate
    :type code_obj: CodeType
    :param str expr: expression corresponding to the code object, for debugging
                     purposes
    :raises NameError: in case a forbidden name (containing two underscores)
                       is found in ``code_obj``

    .. note:: actually forbids every name containing 2 underscores
    """
    for name in code_obj.co_names:
        if "__" in name or name in _UNSAFE_ATTRIBUTES:
            raise NameError('Access to forbidden name %r (%r)' % (name, expr))

def assert_valid_codeobj(allowed_codes, code_obj, expr):
    """ Asserts that the provided code object validates against the bytecode
    and name constraints.

    Recursively validates the code objects stored in its co_consts in case
    lambdas are being created/used (lambdas generate their own separated code
    objects and don't live in the root one)

    :param allowed_codes: list of permissible bytecode instructions
    :type allowed_codes: set(int)
    :param code_obj: code object to name-validate
    :type code_obj: CodeType
    :param str expr: expression corresponding to the code object, for debugging
                     purposes
    :raises ValueError: in case of forbidden bytecode in ``code_obj``
    :raises NameError: in case a forbidden name (containing two underscores)
                       is found in ``code_obj``
    """
    assert_no_dunder_name(code_obj, expr)

    # almost twice as fast as a manual iteration + condition when loading
    # /web according to line_profiler
    codes = set(_get_opcodes(code_obj)) - allowed_codes
    if codes:
        raise ValueError("forbidden opcode(s) in %r: %s" % (expr, ', '.join(opname[x] for x in codes)))

    for const in code_obj.co_consts:
        if isinstance(const, CodeType):
            assert_valid_codeobj(allowed_codes, const, 'lambda')

def test_expr(expr, allowed_codes, mode="eval"):
    """test_expr(expression, allowed_codes[, mode]) -> code_object

    Test that the expression contains only the allowed opcodes.
    If the expression is valid and contains only allowed codes,
    return the compiled code object.
    Otherwise raise a ValueError, a Syntax Error or TypeError accordingly.
    """
    try:
        if mode == 'eval':
            # eval() does not like leading/trailing whitespace
            expr = expr.strip()
        code_obj = compile(expr, "", mode)
    except (SyntaxError, TypeError, ValueError):
        raise
    except Exception as e:
        exc_info = sys.exc_info()
        pycompat.reraise(ValueError, ValueError('"%s" while compiling\n%r' % (ustr(e), expr)), exc_info[2])
    assert_valid_codeobj(allowed_codes, code_obj, expr)
    return code_obj


def const_eval(expr):
    """const_eval(expression) -> value

    Safe Python constant evaluation

    Evaluates a string that contains an expression describing
    a Python constant. Strings that are not valid Python expressions
    or that contain other code besides the constant raise ValueError.

    >>> const_eval("10")
    10
    >>> const_eval("[1,2, (3,4), {'foo':'bar'}]")
    [1, 2, (3, 4), {'foo': 'bar'}]
    >>> const_eval("1+2")
    Traceback (most recent call last):
    ...
    ValueError: opcode BINARY_ADD not allowed
    """
    c = test_expr(expr, _CONST_OPCODES)
    return unsafe_eval(c)

def expr_eval(expr):
    """expr_eval(expression) -> value

    Restricted Python expression evaluation

    Evaluates a string that contains an expression that only
    uses Python constants. This can be used to e.g. evaluate
    a numerical expression from an untrusted source.

    >>> expr_eval("1+2")
    3
    >>> expr_eval("[1,2]*2")
    [1, 2, 1, 2]
    >>> expr_eval("__import__('sys').modules")
    Traceback (most recent call last):
    ...
    ValueError: opcode LOAD_NAME not allowed
    """
    c = test_expr(expr, _EXPR_OPCODES)
    return unsafe_eval(c)

def _import(name, globals=None, locals=None, fromlist=None, level=-1):
    if globals is None:
        globals = {}
    if locals is None:
        locals = {}
    if fromlist is None:
        fromlist = []
    if name in _ALLOWED_MODULES:
        return __import__(name, globals, locals, level)
    raise ImportError(name)
_BUILTINS = {
    '__import__': _import,
    'True': True,
    'False': False,
    'None': None,
    'bytes': bytes,
    'str': str,
    'unicode': pycompat.text_type,
    'bool': bool,
    'int': int,
    'float': float,
    'enumerate': enumerate,
    'dict': dict,
    'list': list,
    'tuple': tuple,
    'map': map,
    'abs': abs,
    'min': min,
    'max': max,
    'sum': sum,
    'reduce': functools.reduce,
    'filter': filter,
    'round': round,
    'len': len,
    'repr': repr,
    'set': set,
    'all': all,
    'any': any,
    'ord': ord,
    'chr': chr,
    'divmod': divmod,
    'isinstance': isinstance,
    'range': range,
    'xrange': range,
    'zip': zip,
    'Exception': Exception,
}
def safe_eval(expr, globals_dict=None, locals_dict=None, mode="eval", nocopy=False, locals_builtins=False):
    """safe_eval(expression[, globals[, locals[, mode[, nocopy]]]]) -> result

    System-restricted Python expression evaluation

    Evaluates a string that contains an expression that mostly
    uses Python constants, arithmetic expressions and the
    objects directly provided in context.

    This can be used to e.g. evaluate
    an OpenERP domain expression from an untrusted source.

    :throws TypeError: If the expression provided is a code object
    :throws SyntaxError: If the expression provided is not valid Python
    :throws NameError: If the expression provided accesses forbidden names
    :throws ValueError: If the expression provided uses forbidden bytecode
    """
    if type(expr) is CodeType:
        raise TypeError("safe_eval does not allow direct evaluation of code objects.")

    # prevent altering the globals/locals from within the sandbox
    # by taking a copy.
    if not nocopy:
        # isinstance() does not work below, we want *exactly* the dict class
        if (globals_dict is not None and type(globals_dict) is not dict) \
                or (locals_dict is not None and type(locals_dict) is not dict):
            _logger.warning(
                "Looks like you are trying to pass a dynamic environment, "
                "you should probably pass nocopy=True to safe_eval().")
        if globals_dict is not None:
            globals_dict = dict(globals_dict)
        if locals_dict is not None:
            locals_dict = dict(locals_dict)

    if globals_dict is None:
        globals_dict = {}

    globals_dict['__builtins__'] = _BUILTINS
    if locals_builtins:
        if locals_dict is None:
            locals_dict = {}
        locals_dict.update(_BUILTINS)
    c = test_expr(expr, _SAFE_OPCODES, mode=mode)
    try:
        return unsafe_eval(c, globals_dict, locals_dict)
    except odoo.exceptions.except_orm:
        raise
    except odoo.exceptions.Warning:
        raise
    except odoo.exceptions.RedirectWarning:
        raise
    except odoo.exceptions.AccessDenied:
        raise
    except odoo.exceptions.AccessError:
        raise
    except werkzeug.exceptions.HTTPException:
        raise
    except odoo.http.AuthenticationError:
        raise
    except OperationalError:
        # Do not hide PostgreSQL low-level exceptions, to let the auto-replay
        # of serialized transactions work its magic
        raise
    except odoo.exceptions.MissingError:
        raise
    except Exception as e:
        exc_info = sys.exc_info()
        pycompat.reraise(ValueError, ValueError('%s: "%s" while evaluating\n%r' % (ustr(type(e)), ustr(e), expr)), exc_info[2])
def test_python_expr(expr, mode="eval"):
    try:
        test_expr(expr, _SAFE_OPCODES, mode=mode)
    except (SyntaxError, TypeError, ValueError) as err:
        if len(err.args) >= 2 and len(err.args[1]) >= 4:
            error = {
                'message': err.args[0],
                'filename': err.args[1][0],
                'lineno': err.args[1][1],
                'offset': err.args[1][2],
                'error_line': err.args[1][3],
            }
            msg = "%s : %s at line %d\n%s" % (type(err).__name__, error['message'], error['lineno'], error['error_line'])
        else:
            msg = ustr(err)
        return msg
    return False
