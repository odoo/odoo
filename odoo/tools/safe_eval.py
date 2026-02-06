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
import ast
import contextvars
import dis
import functools
import gc
import logging
import os
import re
import signal
import sys
import types
import typing
import zoneinfo
from collections import defaultdict, OrderedDict
from enum import auto, Enum
from json.encoder import c_make_encoder
from opcode import opmap, opname
from types import CodeType
from weakref import WeakKeyDictionary

import werkzeug
from psycopg2 import OperationalError

import odoo.exceptions
from .func import lazy
from .misc import OrderedSet

unsafe_eval = eval

__all__ = ['const_eval', 'safe_eval']

_logger = logging.getLogger(__name__)
_logger_runtime = logging.getLogger(f'{__name__}.runtime')


class UnsafePolicy(Enum):
    DISABLE = 0
    LOG = auto()
    RAISE = auto()
    TERMINATE = auto()


try:
    UNSAFE_POLICY = UnsafePolicy[os.environ['ODOO_UNSAFE_POLICY'].upper()]
except KeyError:
    UNSAFE_POLICY = UnsafePolicy.LOG

if UNSAFE_POLICY and c_make_encoder is None:
    _logger_runtime.warning(
        "Unsafe object policy '%s' is configured, but it is not supported on this runtime "
        "(missing native encoder). The policy will be ignored.",
        UNSAFE_POLICY,
    )
    UNSAFE_POLICY = UnsafePolicy.DISABLE


class UnsafeObjectError(BaseException):

    def __init__(self, obj):
        super().__init__(
            'Unsafe object access (type %r): %r (path: %s)' % (
                type(obj), obj, safe_whitelist.get_full_path(obj),
            ),
        )


# The time module is usually already provided in the safe_eval environment
# but some code, e.g. datetime.datetime.now() (Windows/Python 2.5.2, bug
# lp:703841), does import time.
_ALLOWED_MODULES = ['_strptime', 'math', 'time']

# Mock __import__ function, as called by cpython's import emulator `PyImport_Import` inside
# timemodule.c, _datetimemodule.c and others.
# This function does not actually need to do anything, its expected side-effect is to make the
# imported module available in `sys.modules`. The _ALLOWED_MODULES are imported below to make it so.
def _import(name, globals=None, locals=None, fromlist=None, level=-1):
    if name not in sys.modules:
        raise ImportError(f'module {name} should be imported before calling safe_eval()')

for module in _ALLOWED_MODULES:
    __import__(module)


_UNSAFE_ATTRIBUTES = [
    # Frames
    'f_builtins', 'f_code', 'f_globals', 'f_locals',
    # Python 2 functions
    'func_code', 'func_globals',
    # Code object
    'co_code', '_co_code_adaptive',
    # Method resolution order,
    'mro',
    # Tracebacks
    'tb_frame',
    # Generators
    'gi_code', 'gi_frame', 'gi_yieldfrom',
    # Coroutines
    'cr_await', 'cr_code', 'cr_frame',
    # Coroutine generators
    'ag_await', 'ag_code', 'ag_frame',
]


def to_opcodes(opnames, _opmap=opmap):
    for x in opnames:
        if x in _opmap:
            yield _opmap[x]
# opcodes which absolutely positively must not be usable in safe_eval,
# explicitly subtracted from all sets of valid opcodes just in case
_BLACKLIST = set(to_opcodes([
    # can't provide access to accessing arbitrary modules
    'IMPORT_STAR', 'IMPORT_NAME', 'IMPORT_FROM',
    # could allow replacing or updating core attributes on models & al, setitem
    # can be used to set field values
    'STORE_ATTR', 'DELETE_ATTR',
    # no reason to allow this
    'STORE_GLOBAL', 'DELETE_GLOBAL',
]))
# opcodes necessary to build literal values
_CONST_OPCODES = set(to_opcodes([
    # stack manipulations
    'POP_TOP', 'ROT_TWO', 'ROT_THREE', 'ROT_FOUR', 'DUP_TOP', 'DUP_TOP_TWO',
    'LOAD_CONST',
    'RETURN_VALUE',  # return the result of the literal/expr evaluation
    # literal collections
    'BUILD_LIST', 'BUILD_MAP', 'BUILD_TUPLE', 'BUILD_SET',
    # 3.6: literal map with constant keys https://bugs.python.org/issue27140
    'BUILD_CONST_KEY_MAP',
    'LIST_EXTEND', 'SET_UPDATE',
    # 3.11 replace DUP_TOP, DUP_TOP_TWO, ROT_TWO, ROT_THREE, ROT_FOUR
    'COPY', 'SWAP',
    # Added in 3.11 https://docs.python.org/3/whatsnew/3.11.html#new-opcodes
    'RESUME',
    # 3.12 https://docs.python.org/3/whatsnew/3.12.html#cpython-bytecode-changes
    'RETURN_CONST',
    # 3.13
    'TO_BOOL',
])) - _BLACKLIST

# operations which are both binary and inplace, same order as in doc'
_operations = [
    'POWER', 'MULTIPLY',  # 'MATRIX_MULTIPLY', # matrix operator (3.5+)
    'FLOOR_DIVIDE', 'TRUE_DIVIDE', 'MODULO', 'ADD',
    'SUBTRACT', 'LSHIFT', 'RSHIFT', 'AND', 'XOR', 'OR',
]
# operations on literal values
_EXPR_OPCODES = _CONST_OPCODES.union(to_opcodes([
    'UNARY_POSITIVE', 'UNARY_NEGATIVE', 'UNARY_NOT', 'UNARY_INVERT',
    *('BINARY_' + op for op in _operations), 'BINARY_SUBSCR',
    *('INPLACE_' + op for op in _operations),
    'BUILD_SLICE',
    # comprehensions
    'LIST_APPEND', 'MAP_ADD', 'SET_ADD',
    'COMPARE_OP',
    # specialised comparisons
    'IS_OP', 'CONTAINS_OP',
    'DICT_MERGE', 'DICT_UPDATE',
    # Basically used in any "generator literal"
    'GEN_START',  # added in 3.10 but already removed from 3.11.
    # Added in 3.11, replacing all BINARY_* and INPLACE_*
    'BINARY_OP',
    'BINARY_SLICE',
])) - _BLACKLIST

_SAFE_OPCODES = _EXPR_OPCODES.union(to_opcodes([
    'POP_BLOCK', 'POP_EXCEPT',

    # note: removed in 3.8
    'SETUP_LOOP', 'SETUP_EXCEPT', 'BREAK_LOOP', 'CONTINUE_LOOP',

    'EXTENDED_ARG',  # P3.6 for long jump offsets.
    'MAKE_FUNCTION', 'CALL_FUNCTION', 'CALL_FUNCTION_KW', 'CALL_FUNCTION_EX',
    # Added in P3.7 https://bugs.python.org/issue26110
    'CALL_METHOD', 'LOAD_METHOD',

    'GET_ITER', 'FOR_ITER', 'YIELD_VALUE',
    'JUMP_FORWARD', 'JUMP_ABSOLUTE', 'JUMP_BACKWARD',
    'JUMP_IF_FALSE_OR_POP', 'JUMP_IF_TRUE_OR_POP', 'POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE',
    'SETUP_FINALLY', 'END_FINALLY',
    # Added in 3.8 https://bugs.python.org/issue17611
    'BEGIN_FINALLY', 'CALL_FINALLY', 'POP_FINALLY',

    'RAISE_VARARGS', 'LOAD_NAME', 'STORE_NAME', 'DELETE_NAME', 'LOAD_ATTR',
    'LOAD_FAST', 'STORE_FAST', 'DELETE_FAST', 'UNPACK_SEQUENCE',
    'STORE_SUBSCR',
    'LOAD_GLOBAL',

    'RERAISE', 'JUMP_IF_NOT_EXC_MATCH',

    # Following opcodes were Added in 3.11
    # replacement of opcodes CALL_FUNCTION, CALL_FUNCTION_KW, CALL_METHOD
    'PUSH_NULL', 'PRECALL', 'CALL', 'KW_NAMES',
    # replacement of POP_JUMP_IF_TRUE and POP_JUMP_IF_FALSE
    'POP_JUMP_FORWARD_IF_FALSE', 'POP_JUMP_FORWARD_IF_TRUE',
    'POP_JUMP_BACKWARD_IF_FALSE', 'POP_JUMP_BACKWARD_IF_TRUE',
    # special case of the previous for IS NONE / IS NOT NONE
    'POP_JUMP_FORWARD_IF_NONE', 'POP_JUMP_BACKWARD_IF_NONE',
    'POP_JUMP_FORWARD_IF_NOT_NONE', 'POP_JUMP_BACKWARD_IF_NOT_NONE',
    # replacement of JUMP_IF_NOT_EXC_MATCH
    'CHECK_EXC_MATCH',
    # new opcodes
    'RETURN_GENERATOR',
    'PUSH_EXC_INFO',
    'NOP',
    'FORMAT_VALUE', 'BUILD_STRING',
    # 3.12 https://docs.python.org/3/whatsnew/3.12.html#cpython-bytecode-changes
    'END_FOR',
    'LOAD_FAST_AND_CLEAR', 'LOAD_FAST_CHECK',
    'POP_JUMP_IF_NOT_NONE', 'POP_JUMP_IF_NONE',
    'CALL_INTRINSIC_1',
    'STORE_SLICE',
    # 3.13
    'CALL_KW', 'LOAD_FAST_LOAD_FAST',
    'STORE_FAST_STORE_FAST', 'STORE_FAST_LOAD_FAST',
    'CONVERT_VALUE', 'FORMAT_SIMPLE', 'FORMAT_WITH_SPEC',
    'SET_FUNCTION_ATTRIBUTE',
])) - _BLACKLIST


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

    # set operations are almost twice as fast as a manual iteration + condition
    # when loading /web according to line_profiler
    code_codes = {i.opcode for i in dis.get_instructions(code_obj)}
    if not allowed_codes >= code_codes:
        raise ValueError("forbidden opcode(s) in %r: %s" % (expr, ', '.join(opname[x] for x in (code_codes - allowed_codes))))

    for const in code_obj.co_consts:
        if isinstance(const, CodeType):
            assert_valid_codeobj(allowed_codes, const, 'lambda')


def compile_codeobj(expr: str, /, filename: str = '<unknown>', mode: typing.Literal['eval', 'exec'] = 'eval'):
    """
        :param str filename: optional pseudo-filename for the compiled expression,
                             displayed for example in traceback frames
        :param str mode: 'eval' if single expression
                         'exec' if sequence of statements
        :return: compiled code object
        :rtype: types.CodeType
    """
    assert mode in ('eval', 'exec')
    try:
        if mode == 'eval':
            expr = expr.strip()  # eval() does not like leading/trailing whitespace

        if UNSAFE_POLICY:
            tree = ast.parse(expr.strip(), mode=mode)
            tree = safe_transformer.visit(tree)
            code_obj = compile(tree, filename or '', mode)
            monitoring_codeobj(code_obj)
            return code_obj

        return compile(expr, filename or '', mode)

    except (SyntaxError, TypeError, ValueError):
        raise
    except Exception as e:
        raise ValueError('%r while compiling\n%r' % (e, expr))


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
    c = compile_codeobj(expr)
    assert_valid_codeobj(_CONST_OPCODES, c, expr)
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
    c = compile_codeobj(expr)
    assert_valid_codeobj(_EXPR_OPCODES, c, expr)
    return unsafe_eval(c)

_BUILTINS = {
    '__import__': _import,
    'True': True,
    'False': False,
    'None': None,
    'bytes': bytes,
    'str': str,
    'unicode': str,
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
    'sorted': sorted,
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


_BUBBLEUP_EXCEPTIONS = (
    odoo.exceptions.UserError,
    odoo.exceptions.RedirectWarning,
    werkzeug.exceptions.HTTPException,
    OperationalError,  # let auto-replay of serialized transactions work its magic
    ZeroDivisionError,
)


def safe_eval(expr, /, context=None, *, mode="eval", filename=None):
    """System-restricted Python expression evaluation

    Evaluates a string that contains an expression that mostly
    uses Python constants, arithmetic expressions and the
    objects directly provided in context.

    This can be used to e.g. evaluate
    a domain expression from an untrusted source.

    :param expr: The Python expression (or block, if ``mode='exec'``) to evaluate.
    :type expr: string | bytes
    :param context: Namespace available to the expression.
                    This dict will be mutated with any variables created during
                    evaluation
    :type context: dict
    :param mode: ``exec`` or ``eval``
    :type mode: str
    :param filename: optional pseudo-filename for the compiled expression,
                     displayed for example in traceback frames
    :type filename: string
    :throws TypeError: If the expression provided is a code object
    :throws SyntaxError: If the expression provided is not valid Python
    :throws NameError: If the expression provided accesses forbidden names
    :throws ValueError: If the expression provided uses forbidden bytecode
    """
    if type(expr) is CodeType:
        raise TypeError("safe_eval does not allow direct evaluation of code objects.")

    assert context is None or type(context) is dict, "Context must be a dict"

    check_values(context)

    globals_dict = dict(context or {}, __builtins__=dict(_BUILTINS))

    c = compile_codeobj(expr, filename=filename, mode=mode)
    assert_valid_codeobj(_SAFE_OPCODES, c, expr)
    try:
        # empty locals dict makes the eval behave like top-level code
        return unsafe_eval(c, globals_dict, None)

    except _BUBBLEUP_EXCEPTIONS:
        raise

    except (Exception, UnsafeObjectError) as e:  # noqa: BLE001
        raise ValueError('%r while evaluating\n%r' % (e, expr))

    finally:
        if context is not None:
            del globals_dict['__builtins__']
            context.update(globals_dict)


def test_python_expr(expr, mode="eval"):
    try:
        c = compile_codeobj(expr, mode=mode)
        assert_valid_codeobj(_SAFE_OPCODES, c, expr)
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
            msg = str(err)
        return msg
    return False


def check_values(d):
    if not d:
        return d
    for v in d.values():
        if isinstance(v, types.ModuleType):
            raise TypeError(f"""Module {v} can not be used in evaluation contexts

Prefer providing only the items necessary for your intended use.

If a "module" is necessary for backwards compatibility, use
`odoo.tools.safe_eval.wrap_module` to generate a wrapper recursively
whitelisting allowed attributes.

Pre-wrapped modules are provided as attributes of `odoo.tools.safe_eval`.
""")
    return d

class wrap_module:
    def __init__(self, module, attributes):
        """Helper for wrapping a package/module to expose selected attributes

        :param module: the actual package/module to wrap, as returned by ``import <module>``
        :param iterable attributes: attributes to expose / whitelist. If a dict,
                                    the keys are the attributes and the values
                                    are used as an ``attributes`` in case the
                                    corresponding item is a submodule
        """
        # builtin modules don't have a __file__ at all
        modfile = getattr(module, '__file__', '(built-in)')
        self._repr = f"<wrapped {module.__name__!r} ({modfile})>"
        for attrib in attributes:
            target = getattr(module, attrib)
            if isinstance(target, types.ModuleType):
                target = wrap_module(target, attributes[attrib])
            setattr(self, attrib, target)

    def __repr__(self):
        return self._repr

# dateutil submodules are lazy so need to import them for them to "exist"
import dateutil
mods = ['parser', 'relativedelta', 'rrule', 'tz']
for mod in mods:
    __import__('dateutil.%s' % mod)

datetime = wrap_module(__import__('datetime'), ['date', 'datetime', 'time', 'timedelta', 'timezone', 'tzinfo', 'MAXYEAR', 'MINYEAR'])
dateutil = wrap_module(dateutil, {
    "tz": ["UTC", "tzutc"],
    "parser": ["isoparse", "parse"],
    "relativedelta": ["relativedelta", "MO", "TU", "WE", "TH", "FR", "SA", "SU"],
    "rrule": ["rrule", "rruleset", "rrulestr", "YEARLY", "MONTHLY", "WEEKLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY", "MO", "TU", "WE", "TH", "FR", "SA", "SU"],
})
json = wrap_module(__import__('json'), ['loads', 'dumps'])
time = wrap_module(__import__('time'), ['time', 'strptime', 'strftime', 'sleep'])
dateutil.tz.gettz = zoneinfo.ZoneInfo


# Runtime verification is performed using three objects:
# - safe_transformer:
#       modifies the code to use the `safe_call` function for each
#       function call
# - safe_encoder:
#       attempts to serialize the objects used during a call
# - safe_whitelist:
#       used during serialization if the objects need to be verified


class _SafeTransformer(ast.NodeTransformer):

    CALL_ID = '.CALL'

    # TODO: Prevent the use of bare excepts by converting them to blind excepts

    def visit_Call(self, node):
        """
        Transforms:
            func(*args, **kwargs)

        Into:
            CALL_ID(func, *args, **kwargs)
        """
        self.generic_visit(node)
        call = ast.Call(
            func=ast.Name(id=self.CALL_ID, ctx=ast.Load()),
            args=[node.func, *node.args],
            keywords=node.keywords)
        ast.copy_location(call, node)
        ast.copy_location(call.func, node)
        return call

    def visit_FunctionDef(self, node):
        """
        Transforms:
            @decorator_A
            @decorator_B
            def func():
                pass

        Into:
            def func():
                pass
            func = CALL_ID(decorator_B, func)
            func = CALL_ID(decorator_A, func)
        """
        self.generic_visit(node)
        stmts = [node]
        while node.decorator_list and (decorator := node.decorator_list.pop()):
            call = ast.Call(
                func=ast.Name(id=self.CALL_ID, ctx=ast.Load()),
                args=[decorator, ast.Name(id=node.name, ctx=ast.Load())],
                keywords=[],
            )
            assign = ast.Assign(
                targets=[ast.Name(id=node.name, ctx=ast.Store())],
                value=call,
            )
            ast.copy_location(call, node)
            ast.copy_location(call.func, node)
            ast.copy_location(call.args[1], node)
            ast.copy_location(assign, node)
            ast.copy_location(assign.targets[0], node)
            stmts.append(assign)
        return stmts


encoder_ctx = contextvars.ContextVar('encoder_ctx')


class _SafeEncoder:

    MAPPINGS = frozenset((dict, defaultdict, OrderedDict, types.MappingProxyType))
    SEQUENCES = frozenset((list, tuple, set, frozenset, OrderedSet))

    def __init__(self):
        self.hooks: WeakKeyDictionary[type, typing.Callable | None] = WeakKeyDictionary()
        # Add hooks
        self.hooks.update(dict.fromkeys(_SafeWhitelist.TRUSTED_TYPES, None))  # Optimization to save time when serializing these types
        self.hooks.update(dict.fromkeys(self.SEQUENCES, list))
        self.hooks.update(dict.fromkeys(self.MAPPINGS, dict))
        self.hooks[type] = self._hook_class
        self.hooks[types.ModuleType] = self._hook_module
        self.hooks[types.BuiltinFunctionType] = self._hook_builtin_function
        self.hooks[types.BuiltinMethodType] = self._hook_builtin_function
        self.hooks[types.FunctionType] = self._hook_function
        self.hooks[types.MethodType] = self._hook_function
        self.hooks[types.MethodDescriptorType] = self._hook_descriptor
        self.hooks[functools.partial] = self._hook_partial
        self.hooks[lazy] = self._hook_lazy
        self.hooks[type(reversed([]))] = self._hook_simple_iterator
        d = {}
        self.hooks[type(d.items())] = list
        self.hooks[type(d.keys())] = list
        self.hooks[type(d.values())] = list
        d = OrderedDict()
        self.hooks[type(d.items())] = list
        self.hooks[type(d.keys())] = list
        self.hooks[type(d.values())] = list
        self.hooks[types.GeneratorType] = None  # TODO: Make the hook (to listen for the yield event)

    @property
    def _encoder(self):
        # Encoder must be thread safe (because of the markers structure)
        try:
            encoder = encoder_ctx.get()
        except LookupError:
            # markers, default, encoder, indent, key_separator, item_separator, sort_keys, skipkeys, allow_nan
            encoder = c_make_encoder({}, self._default, lambda x: '', None, '', '', False, False, False)
            encoder_ctx.set(encoder)
        encoder.markers.clear()
        return encoder

    def encode(self, obj) -> None:
        """
        Perform a safety encoding on the given object to determine if it is
        considered "safe" according to the rules defined in `SafeWhitelist`.

        This method attempts to encode the object using a JSON encoder,
        which validates the object's type and contents recursively.

        :param obj: The object to be checked for safety.
        :raises UnsafeObjectError: If the object or any nested element is
                                   determined to be unsafe.
        """
        try:
            self._encoder(obj, 0)
            return
        except (ValueError, TypeError, KeyError):
            pass

        stack = [obj]
        seen = set()
        while stack:
            o = stack.pop()
            if (id_o := id(o)) in seen:
                continue
            seen.add(id_o)
            try:
                self._encoder(o, 0)
            except (ValueError, TypeError, KeyError) as e:
                collection_o = self._default(o)
                if type(collection_o) in self.MAPPINGS:
                    stack.extend(collection_o.keys())
                    stack.extend(collection_o.values())
                    continue
                if type(collection_o) in self.SEQUENCES:
                    stack.extend(collection_o)
                    continue
                # Serialisation failure
                _logger_runtime.warning('_json.c_make_encoder: %s %r', e, o)

    def _default(self, obj):
        """ Dispatch to the default check-serialisation function of `obj`. """
        t_obj = type(obj)
        try:
            hook = self.hooks[t_obj]
        except KeyError:
            if isinstance(obj, type):
                hook = self._hook_class
            else:
                hook = self._hook_instance
            self.hooks[t_obj] = hook

        if not hook:
            return None

        return hook(obj)

    def _hook_simple_iterator(self, obj):
        return gc.get_referents(obj)[-1]

    def _hook_module(self, obj):
        safe_whitelist.check_module(obj)

    def _hook_builtin_function(self, obj):
        if obj in safe_whitelist.TRUSTED_BUILTIN_FUNCTIONS:
            return
        safe_whitelist.check_function(obj)

    def _hook_function(self, obj):
        if getattr(obj, '__module__', False):  # Not user-defined
            safe_whitelist.check_function(obj)

    def _hook_descriptor(self, obj):
        if hasattr(obj, '__objclass__'):  # Not bound
            safe_whitelist.check_function(obj)

    def _hook_partial(self, obj):
        return (obj.func, obj.args, obj.keywords)

    def _hook_lazy(self, obj):
        if getattr(obj, '_func', None) is None:
            return obj._cached_value
        return (obj._func, obj._args, obj._kwargs)

    def _hook_class(self, obj):
        if obj in safe_whitelist.TRUSTED_TYPES:
            return
        safe_whitelist.check_class(obj)

    def _hook_instance(self, obj):
        safe_whitelist.check_instance(obj)


class _SafeWhitelist:

    RE_NOTHING = re.compile(r'(?!)')
    TRUSTED_TYPES = frozenset((
        *_SafeEncoder.MAPPINGS, *_SafeEncoder.SEQUENCES,
        object, bool, int, float, str, bytes, bytearray, memoryview,
        types.NoneType,
        filter, map, enumerate, range, zip, reversed,
        Exception, ValueError, TypeError, AttributeError, KeyError, ZeroDivisionError, UnboundLocalError,
    ))
    TRUSTED_BUILTIN_FUNCTIONS = frozenset((
        min, max, sum, abs, sorted, round, len, repr, all, any, ord, chr, divmod,
        isinstance, hasattr,
    ))

    @staticmethod
    def get_full_path(cls_obj: type) -> str:
        try:
            qualname = cls_obj.__qualname__
        except (AttributeError, RuntimeError):
            qualname = ''
        if (module := getattr(cls_obj, '__module__', None)) and module in sys.modules:
            return f"{module}.{qualname}".strip('.')
        if type(cls_obj) is types.ModuleType:
            return cls_obj.__name__
        return qualname

    def __init__(self):
        self._classes = set()
        self._instances = set()
        self._functions = set()

    def add_class(self, value: tuple) -> None:
        self._classes.add(value)
        self.add_instance(value)
        vars(self).pop('_re_class', None)

    def add_instance(self, value: tuple) -> None:
        self._instances.add(value)
        # Trust function of the class/instance implicitly
        if value[-1] != '*':
            value += ('*',)
        self.add_function(value)
        vars(self).pop('_re_instance', None)

    def add_function(self, value: tuple) -> None:
        self._functions.add(value)
        vars(self).pop('_re_function', None)

    _re_class = functools.cached_property(lambda self: self._re_compile(self._classes))
    _re_instance = functools.cached_property(lambda self: self._re_compile(self._instances))
    _re_function = functools.cached_property(lambda self: self._re_compile(self._functions))

    def _re_compile(self, trusted: set) -> typing.Pattern:
        _initialize_safe_whitelist()
        if not trusted:
            self.RE_NOTHING

        # Make the trie
        trie = {}
        for path in trusted:
            nodes = [trie]
            for part in path:
                part = part if isinstance(part, tuple) else (part,)
                next_nodes = []
                for node in nodes:
                    for p in part:
                        child = node.setdefault(p, {})
                        next_nodes.append(child)
                nodes = next_nodes

        # Convert the trie to regex
        def _trie_to_regex(trie):
            if not trie:
                return ''

            re_parts = []
            for key, subtree in trie.items():
                subpattern = '.+' if key == '*' else re.escape(key)
                if child_pattern := _trie_to_regex(subtree):
                    re_parts.append(subpattern + r'\.' + child_pattern)
                else:
                    re_parts.append(subpattern)

            # non-capturing group only if multiple alternatives
            if len(re_parts) == 1:
                return re_parts[0]
            return '(?:' + '|'.join(re_parts) + ')'

        return re.compile(_trie_to_regex(trie))

    def check_class(self, obj):
        if not self._re_class.fullmatch(self.get_full_path(obj)):
            raise UnsafeObjectError(obj)

    def check_instance(self, obj):
        obj = type(obj)
        if not self._re_instance.fullmatch(self.get_full_path(obj)):
            raise UnsafeObjectError(obj)

    def check_function(self, obj):
        if not self._re_function.fullmatch(self.get_full_path(obj)):
            raise UnsafeObjectError(obj)

    def check_module(self, obj):
        raise UnsafeObjectError(obj)


# Make global objects for this module for performance
safe_transformer = _SafeTransformer()
safe_encoder = _SafeEncoder()
safe_whitelist = _SafeWhitelist()


def safe_call(callee, /, *args, **kwargs):
    """ Ensure objects used for the call are safe """
    try:
        safe_encoder.encode((callee, args, kwargs))
    except UnsafeObjectError as e:
        _logger_runtime.warning(e)
        if UNSAFE_POLICY == UnsafePolicy.RAISE:
            raise
        if UNSAFE_POLICY == UnsafePolicy.TERMINATE:
            os.kill(os.getpid(), signal.SIGKILL)
    return callee(*args, **kwargs)


def monitoring_call(code, instruction_offset, callee, arg0):
    """ Ensure `safe_call` is not overridden """
    if callee is safe_call:
        return
    frame = sys._getframe(1)
    call_id = safe_transformer.CALL_ID
    assert (call_func := frame.f_locals.get(call_id)) is None or call_func is safe_call
    assert (call_func := frame.f_globals.get(call_id)) is None or call_func is safe_call
    assert frame.f_builtins[call_id] is safe_call


_BUILTINS[safe_transformer.CALL_ID] = safe_call

EVENTS = sys.monitoring.events
TOOL_ID = 4  # Not prevent other tools from using "official IDs"
sys.monitoring.use_tool_id(TOOL_ID, 'ODOO_UNSAFE_POLICY_TOOL')
sys.monitoring.register_callback(TOOL_ID, EVENTS.CALL, monitoring_call)


def monitoring_codeobj(code):
    codes = [code]
    while codes:
        code = codes.pop()
        sys.monitoring.set_local_events(TOOL_ID, code, EVENTS.CALL)
        codes.extend(const for const in code.co_consts if isinstance(const, types.CodeType))


@functools.cache
def _initialize_safe_whitelist():
    # C functions
    safe_whitelist.add_function((('bool', 'int', 'float', 'str', 'bytes', 'list', 'tuple', 'set', 'dict', 'mappingproxy'), '*'))
    # Monkeypatches
    safe_whitelist.add_instance(('odoo', '_monkeypatches', 'zoneinfo', 'ZoneInfo'))
    safe_whitelist.add_function(('odoo', '_monkeypatches', '*'))
    # Addons
    safe_whitelist.add_class(('odoo', 'addons', '*'))  # TODO: Restrict addons
    # ORM
    safe_whitelist.add_class(('odoo', 'orm', (
        'domains',
        'fields',
        'fields_selection',
        'models',
    ), '*'))
    safe_whitelist.add_class(('odoo', 'orm', 'commands', 'Command'))
    safe_whitelist.add_instance(('odoo', 'orm', 'environments', 'Environment'))
    safe_whitelist.add_instance(('odoo', 'orm', 'identifiers', 'NewId'))
    safe_whitelist.add_instance(('odoo', 'orm', 'registry', 'Registry'))
    # Exceptions
    safe_whitelist.add_class(('odoo', 'exceptions', ('AccessDenied', 'AccessError', 'MissingError', 'UserError', 'ValidationError')))
    # Tools
    safe_whitelist.add_class(('odoo', 'tools', 'convert', 'xml_import'))
    safe_whitelist.add_class(('odoo', 'tools', 'func', 'lazy'))
    safe_whitelist.add_class(('odoo', 'tools', 'json', ('_ScriptSafe', 'JSON')))
    safe_whitelist.add_class(('odoo', 'tools', 'profiler', 'QwebTracker'))
    safe_whitelist.add_class(('odoo', 'tools', 'safe_eval', 'wrap_module'))
    safe_whitelist.add_instance(('odoo', 'tools', 'misc', ('OrderedSet', 'ReversedIterable')))
    safe_whitelist.add_instance(('odoo', 'tools', 'query', 'Query'))
    safe_whitelist.add_instance(('odoo', 'tools', 'translate', 'LazyGettext'))
    safe_whitelist.add_function(('odoo', 'tools', 'float_utils', ('float_compare', 'float_repr', 'float_round')))
    safe_whitelist.add_function(('odoo', 'tools', 'mail', ('formataddr', 'html2plaintext', 'is_html_empty')))
    safe_whitelist.add_function(('odoo', 'tools', 'misc', ('format_amount', 'format_date', 'format_duration', 'street_split')))
    safe_whitelist.add_function(('odoo', 'tools', 'safe_eval', '_import'))
    safe_whitelist.add_function(('odoo', 'tools', 'translate', 'html_translate'))
    # HTTP
    safe_whitelist.add_instance(('odoo', 'http', '_facade', ('HTTPRequest', 'SafeResponse')))
    safe_whitelist.add_instance(('odoo', 'http', 'geoip', 'GeoIP'))
    safe_whitelist.add_instance(('odoo', 'http', 'requestlib', 'Request'))
    safe_whitelist.add_instance(('odoo', 'http', 'response', 'Response'))
    safe_whitelist.add_instance(('odoo', 'http', 'session', 'Session'))
    # SQL - DB
    safe_whitelist.add_class(('psycopg2', ('InterfaceError', 'OperationalError', 'ProgrammingError')))
    safe_whitelist.add_class(('psycopg2', 'errors', '*'))
    safe_whitelist.add_class(('psycopg2', 'extensions', 'TransactionRollbackError'))
    safe_whitelist.add_instance(('odoo', 'sql_db', 'Cursor'))
    safe_whitelist.add_function(('cursor', ('fetchall', 'fetchone')))
    # Datetime - Date - Timezone
    safe_whitelist.add_class(('datetime', ('date', 'datetime', 'time', 'timedelta', 'timezone')))
    safe_whitelist.add_class(('dateutil', 'relativedelta', 'relativedelta'))
    safe_whitelist.add_instance(('pytz', ('tzfile', 'UTC')))
    safe_whitelist.add_function((('date', 'datetime', 'time'), '*'))
    safe_whitelist.add_function(('pytz', 'tzinfo', 'DstTzInfo', 'localize'))
    safe_whitelist.add_function(('pytz', 'UTC', 'localize'))
    # Miscellaneous
    safe_whitelist.add_class(('collections', ('defaultdict', 'OrderedDict')))
    safe_whitelist.add_class(('collections', 'abc', ('Mapping', 'Sized', 'ValuesView')))
    safe_whitelist.add_class(('itertools', 'islice'))
    safe_whitelist.add_class(('markupsafe', '*'))
    safe_whitelist.add_instance(('email', 'headerregistry', '_UniqueAddressHeader'))
    safe_whitelist.add_instance(('email', 'message', 'EmailMessage'))
    safe_whitelist.add_instance(('json', 'decoder', 'JSONDecodeError'))
    safe_whitelist.add_instance(('lxml', 'etree', '_Element'))
    safe_whitelist.add_instance(('uuid', 'UUID'))
    safe_whitelist.add_function(('_functools', 'reduce'))
    safe_whitelist.add_function((('defaultdict', 'OrderedDict', 'math'), '*'))
    safe_whitelist.add_function(('base64', ('b64decode', 'b64encode', 'urlsafe_b64decode', 'urlsafe_b64encode')))
    safe_whitelist.add_function(('urllib', 'parse', 'quote'))
    # Werkzeug
    safe_whitelist.add_class(('werkzeug', 'datastructures', 'structures', ('ImmutableMultiDict', 'MultiDict')))
    safe_whitelist.add_class(('werkzeug', 'exceptions', ('BadRequest', 'Forbidden', 'NotFound', 'RequestEntityTooLarge', 'Unauthorized')))
    safe_whitelist.add_instance(('werkzeug', 'datastructures', 'file_storage', 'FileStorage'))
    safe_whitelist.add_instance(('werkzeug', 'local', 'LocalProxy'))
    safe_whitelist.add_function(('werkzeug', 'datastructures', 'structures', 'TypeConversionDict', '*'))
