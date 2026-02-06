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
import sys
import types
import typing
import zoneinfo
from collections import defaultdict, OrderedDict
from enum import auto, IntEnum
from json.encoder import c_make_encoder
from opcode import opmap, opname
from types import CodeType
from weakref import WeakKeyDictionary

import werkzeug
from psycopg2 import OperationalError

import odoo.exceptions
from .config import config
from .func import lazy
from .misc import OrderedSet

unsafe_eval = eval

__all__ = ['const_eval', 'safe_eval']

_logger = logging.getLogger(__name__)
_logger_runtime = logging.getLogger(f'{__name__}.runtime')


class UnsafePolicy(IntEnum):
    DISABLE = 0
    LOG = auto()
    RAISE = auto()
    TERMINATE = auto()


@functools.cache
def unsafe_policy():
    policy = UnsafePolicy[config['unsafe_policy'].upper()]

    if policy and c_make_encoder is None:
        _logger_runtime.warning(
            "Unsafe object policy '%s' is configured, but it is not supported on this runtime "
            "(missing native encoder). The policy will be ignored.",
            policy.name,
        )
        policy = UnsafePolicy.DISABLE

    return policy


class UnsafeObjectError(BaseException):

    def __init__(self, obj):
        obj_path = safe_whitelist.get_full_path(obj)
        super().__init__(
            f'Unsafe object access (type {type(obj)!r}): {obj!r} (path: {obj_path})',
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
    'f_builtins', 'f_code', 'f_globals', 'f_locals', 'f_generator',
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
    # 3.14 https://docs.python.org/3/whatsnew/3.14.html#cpython-bytecode-changes
    'LOAD_SMALL_INT',
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
    # 3.14
    'LOAD_FAST_BORROW', 'LOAD_FAST_BORROW_LOAD_FAST_BORROW',  # LOAD_FAST optimizations
    'POP_ITER',
    # Hardcoded list of constants, does not bypasses __builtins__
    # c.f. https://github.com/python/cpython/blob/9181d776daf87f0e4e2ce02c08f162150fdf7d79/Python/pylifecycle.c#L830-L836
    'LOAD_COMMON_CONSTANT',
    'NOT_TAKEN',
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

        if unsafe_policy():
            tree = ast.parse(expr, mode=mode)
            tree = safe_transform(tree)
            code_obj = compile(tree, filename or '', mode)
            add_monitoring(code_obj)
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
# - safe_transformer: modifies the code to use the `safe_call` function
#                     for each function call
# - safe_checker: verifies the objects used during a call
# - safe_whitelist: used during verifications


class _SafeTransformer(ast.NodeTransformer):
    """
    Code transformer that wraps calls with :func:`_save_eval_call` in
    order to check that the arguments are "safe".
    """

    # In Qweb, we use the transformer to modify the python expression.
    # The ast will not be compiled, but instead "unparsed" in the transpiled template.
    # The expression will be used later and therefore re-parsed.
    # It is therefore necessary for the identifiers to be valid.

    CALL_ID = '_save_eval_call'

    def visit_Call(self, node):
        """
        Transforms:
            func(*args, **kwargs)

        Into:
            _save_eval_call(func, *args, **kwargs)
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
            @decorator_A()
            @decorator_B()
            def func():
                pass

        Into:
            def func():
                pass

            func = _save_eval_call(_save_eval_call(decorator_A), _save_eval_call(_save_eval_call(decorator_B), func))
        """
        self.generic_visit(node)
        if not node.decorator_list:
            return node

        current_wrapper = ast.Name(id=node.name, ctx=ast.Load())
        ast.copy_location(current_wrapper, node)

        while node.decorator_list:
            decorator = node.decorator_list.pop()
            current_wrapper = ast.Call(
                func=ast.Name(id=self.CALL_ID, ctx=ast.Load()),
                args=[
                    decorator,
                    current_wrapper,
                ],
                keywords=[],
            )
            ast.copy_location(current_wrapper, node)
            ast.copy_location(current_wrapper.func, node)

        assign = ast.Assign(
            targets=[ast.Name(id=node.name, ctx=ast.Store())],
            value=current_wrapper,
        )
        ast.copy_location(assign, node)
        ast.copy_location(assign.targets[0], node)

        return [node, assign]


encoder_ctx = contextvars.ContextVar('encoder_ctx')


class _SafeChecker:
    """
    Callable object that checks whether a value is considered "safe".
    It does so by using on a JSON encoder, for which one can add type-specific hooks.
    An empty hook simply considers the given type as completely safe,
    while other hooks may check a value and return values to be recursively checked.
    """

    MAPPINGS = frozenset((dict, defaultdict, OrderedDict, types.MappingProxyType))
    SEQUENCES = frozenset((list, tuple, set, frozenset, OrderedSet))

    def __init__(self):
        self.__hooks: WeakKeyDictionary[type, typing.Callable | None] = WeakKeyDictionary()
        # Add hooks
        for t in _SafeWhitelist.TRUSTED_TYPES: self.add_hook(t, None)  # Optimization to save time when serializing these types  # noqa: E701
        for t in self.SEQUENCES: self.add_hook(t, list)  # noqa: E701
        for t in self.MAPPINGS: self.add_hook(t, dict)  # noqa: E701
        self.add_hook(type, self._hook_class)
        self.add_hook(types.ModuleType, self._hook_module)
        self.add_hook(types.BuiltinFunctionType, self._hook_builtin_function)
        self.add_hook(types.BuiltinMethodType, self._hook_builtin_function)
        self.add_hook(types.FunctionType, self._hook_function)
        self.add_hook(types.MethodType, self._hook_function)
        self.add_hook(types.MethodDescriptorType, self._hook_descriptor)
        self.add_hook(functools.partial, self._hook_partial)
        self.add_hook(lazy, self._hook_lazy)
        self.add_hook(type(reversed([])), self._hook_simple_iterator)
        d = {}
        self.add_hook(type(d.items()), list)
        self.add_hook(type(d.keys()), list)
        self.add_hook(type(d.values()), list)
        d = OrderedDict()
        self.add_hook(type(d.items()), list)
        self.add_hook(type(d.keys()), list)
        self.add_hook(type(d.values()), list)
        self.add_hook(types.GeneratorType, None)  # TODO: Make the hook (to listen for the yield event)

    def add_hook(self, type_: type, hook: typing.Callable | None = None) -> None:
        self.__hooks[type_] = hook

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

    def check(self, obj) -> None:
        """
        Check whether the given object is considered "safe" according to
        the rules defined in `SafeWhitelist`.

        This method attempts to encode the object using a JSON encoder,
        which validates the object's type and contents recursively.

        :param obj: The object to be checked for safety.
        :raises UnsafeObjectError: If the object or any nested element
                                   is determined to be unsafe.
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
            hook = self.__hooks[t_obj]
        except KeyError:
            if isinstance(obj, type):
                hook = self._hook_class
            else:
                hook = self._hook_instance
            self.__hooks[t_obj] = hook

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
        if obj is safe_call:
            return
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
    """
    Maintains a whitelist of trusted objects, which can be defined using
    three methods: `add_class`, `add_instance` and `add_function`.

    Each method accepts the fully qualified name of the object to trust.
    A wildcard '*' at the end of a qualified name to trust all objects
    within subpath namespace.

    .. code-block:: python
        safe_whitelist.add_class('odoo.orm.models.*')
        safe_whitelist.add_instance('odoo.orm.environments.Environment')
        safe_whitelist.add_function('odoo.tools.float_utils.float_compare')
    """

    RE_NOTHING = re.compile(r'(?!)')
    TRUSTED_TYPES = frozenset((
        *_SafeChecker.MAPPINGS, *_SafeChecker.SEQUENCES,
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

        if module := getattr(cls_obj, '__module__', None):
            if module in sys.modules:
                return f'{module}.{qualname}'.strip('.')

            # The object can be defined in a module which is not register,
            # for example via `load_script`. It is the case for upgrade.
            if code := getattr(cls_obj, '__code__', None):
                file_path = os.path.abspath(code.co_filename)
                for upgrade_path in config['upgrade_path']:
                    upgrade_path = os.path.abspath(upgrade_path)
                    if os.path.commonpath([file_path, upgrade_path]) == upgrade_path:
                        return f'odoo.upgrade.{qualname}'.strip('.')

        if type(cls_obj) is types.ModuleType:
            return cls_obj.__name__
        return qualname

    def __init__(self):
        self._classes = list()
        self._instances = list()
        self._functions = list()

    def add_class(self, qualname: str) -> None:
        self._classes.append(qualname)
        self.add_instance(qualname)
        vars(self).pop('_re_class', None)

    def add_instance(self, qualname: str) -> None:
        self._instances.append(qualname)
        # Trust function of the class/instance implicitly
        if not qualname.endswith('.*'):
            qualname += '.*'
        self.add_function(qualname)
        vars(self).pop('_re_instance', None)

    def add_function(self, qualname: str) -> None:
        self._functions.append(qualname)
        vars(self).pop('_re_function', None)

    _re_class = functools.cached_property(lambda self: self._re_compile(self._classes))
    _re_instance = functools.cached_property(lambda self: self._re_compile(self._instances))
    _re_function = functools.cached_property(lambda self: self._re_compile(self._functions))

    def _re_compile(self, trusted: list) -> typing.Pattern:
        _initialize_safe_whitelist()
        if not trusted:
            return self.RE_NOTHING

        # Make the trie
        trie = {}
        for path in trusted:
            node = trie
            for part in path.split('.'):
                node = node.setdefault(part, {})

        # Convert the trie to regex
        def _trie_to_regex(trie):
            if not trie:
                return ''

            re_parts = []
            for key, subtree in trie.items():
                assert key != '*' or not subtree
                subpattern = '.+' if key == '*' else re.escape(key)
                if child_pattern := _trie_to_regex(subtree):
                    re_parts.append(fr'{subpattern}\.{child_pattern}')
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


safe_transformer = _SafeTransformer()
safe_transform = safe_transformer.visit
safe_checker = _SafeChecker()
safe_whitelist = _SafeWhitelist()


def safe_call(callee, /, *args, **kwargs):
    """ Ensure objects used for the call are safe """
    try:
        safe_checker.check((callee, args, kwargs))
    except UnsafeObjectError as e:
        _logger_runtime.warning(e)
        if unsafe_policy() is UnsafePolicy.RAISE:
            raise
        if unsafe_policy() is UnsafePolicy.TERMINATE:
            os._exit(1)
    return callee(*args, **kwargs)


def monitoring_call(code, instruction_offset, callee, arg0):
    """ Ensure `_save_eval_call` is not overridden """
    if callee is safe_call:
        return
    frame = sys._getframe(1)
    call_id = safe_transformer.CALL_ID
    assert call_id not in frame.f_locals or frame.f_locals[call_id] is safe_call
    assert call_id not in frame.f_globals or frame.f_globals[call_id] is safe_call
    assert frame.f_builtins[call_id] is safe_call


_BUILTINS[safe_transformer.CALL_ID] = safe_call

EVENTS = sys.monitoring.events
TOOL_ID = 4  # Not prevent other tools from using "official IDs"
sys.monitoring.use_tool_id(TOOL_ID, 'ODOO_UNSAFE_POLICY_TOOL')
sys.monitoring.register_callback(TOOL_ID, EVENTS.CALL, monitoring_call)


def add_monitoring(code):
    codes = [code]
    while codes:
        code = codes.pop()
        sys.monitoring.set_local_events(TOOL_ID, code, EVENTS.CALL)
        codes.extend(const for const in code.co_consts if isinstance(const, types.CodeType))


@functools.cache
def _initialize_safe_whitelist():
    # Primitive types and builtins (C functions)
    safe_whitelist.add_function('bool.*')
    safe_whitelist.add_function('int.*')
    safe_whitelist.add_function('float.*')
    safe_whitelist.add_function('str.*')
    safe_whitelist.add_function('bytes.*')
    safe_whitelist.add_function('list.*')
    safe_whitelist.add_function('tuple.*')
    safe_whitelist.add_function('set.*')
    safe_whitelist.add_function('dict.*')
    safe_whitelist.add_function('mappingproxy.*')
    safe_whitelist.add_function('defaultdict.*')
    safe_whitelist.add_function('OrderedDict.*')
    safe_whitelist.add_function('_functools.reduce')
    # Monkey patches
    safe_whitelist.add_instance('odoo._monkeypatches.zoneinfo.ZoneInfo')
    safe_whitelist.add_function('odoo._monkeypatches.*')
    # Core
    safe_whitelist.add_class('odoo.addons.*')  # TODO: Restrict addons
    safe_whitelist.add_class('odoo.upgrade.*')
    safe_whitelist.add_class('odoo.orm.domains.*')
    safe_whitelist.add_class('odoo.orm.fields.*')
    safe_whitelist.add_class('odoo.orm.fields_binary.*')
    safe_whitelist.add_class('odoo.orm.fields_selection.*')
    safe_whitelist.add_class('odoo.orm.models.*')
    safe_whitelist.add_class('odoo.orm.commands.Command')
    safe_whitelist.add_instance('odoo.orm.environments.Environment')
    safe_whitelist.add_instance('odoo.orm.identifiers.NewId')
    safe_whitelist.add_instance('odoo.orm.registry.Registry')
    safe_whitelist.add_class('odoo.exceptions.AccessDenied')
    safe_whitelist.add_class('odoo.exceptions.AccessError')
    safe_whitelist.add_class('odoo.exceptions.MissingError')
    safe_whitelist.add_class('odoo.exceptions.UserError')
    safe_whitelist.add_class('odoo.exceptions.ValidationError')
    # HTTP
    safe_whitelist.add_instance('odoo.http._facade.HTTPRequest')
    safe_whitelist.add_instance('odoo.http._facade.SafeResponse')
    safe_whitelist.add_instance('odoo.http.geoip.GeoIP')
    safe_whitelist.add_instance('odoo.http.requestlib.Request')
    safe_whitelist.add_instance('odoo.http.response.Response')
    safe_whitelist.add_instance('odoo.http.session.Session')
    # Database
    safe_whitelist.add_instance('odoo.sql_db.Cursor')
    # Tools
    safe_whitelist.add_class('odoo.tools.binary.*')
    safe_whitelist.add_class('odoo.tools.convert.xml_import')
    safe_whitelist.add_class('odoo.tools.func.lazy')
    safe_whitelist.add_class('odoo.tools.json._ScriptSafe')
    safe_whitelist.add_class('odoo.tools.json.JSON')
    safe_whitelist.add_class('odoo.tools.profiler.QwebTracker')
    safe_whitelist.add_class('odoo.tools.safe_eval.wrap_module')
    safe_whitelist.add_instance('odoo.tools.misc.OrderedSet')
    safe_whitelist.add_instance('odoo.tools.misc.ReversedIterable')
    safe_whitelist.add_instance('odoo.tools.query.Query')
    safe_whitelist.add_instance('odoo.tools.translate.LazyGettext')
    safe_whitelist.add_function('odoo.tools.float_utils.float_compare')
    safe_whitelist.add_function('odoo.tools.float_utils.float_is_zero')
    safe_whitelist.add_function('odoo.tools.float_utils.float_repr')
    safe_whitelist.add_function('odoo.tools.float_utils.float_round')
    safe_whitelist.add_function('odoo.tools.mail.formataddr')
    safe_whitelist.add_function('odoo.tools.mail.html2plaintext')
    safe_whitelist.add_function('odoo.tools.mail.is_html_empty')
    safe_whitelist.add_function('odoo.tools.misc.format_amount')
    safe_whitelist.add_function('odoo.tools.misc.format_date')
    safe_whitelist.add_function('odoo.tools.misc.format_duration')
    safe_whitelist.add_function('odoo.tools.misc.street_split')
    safe_whitelist.add_function('odoo.tools.safe_eval._import')
    safe_whitelist.add_function('odoo.tools.translate.html_translate')
    # Psycopg2
    safe_whitelist.add_class('psycopg2.InterfaceError')
    safe_whitelist.add_class('psycopg2.OperationalError')
    safe_whitelist.add_class('psycopg2.ProgrammingError')
    safe_whitelist.add_class('psycopg2.errors.*')
    safe_whitelist.add_class('psycopg2.extensions.TransactionRollbackError')
    # Cursor
    safe_whitelist.add_function('cursor.fetchall')
    safe_whitelist.add_function('cursor.fetchone')
    # Dates - Times - Timezone
    safe_whitelist.add_function('date.*')
    safe_whitelist.add_class('datetime.date')
    safe_whitelist.add_class('datetime.datetime')
    safe_whitelist.add_class('datetime.time')
    safe_whitelist.add_class('datetime.timedelta')
    safe_whitelist.add_class('datetime.timezone')
    safe_whitelist.add_function('datetime.*')
    safe_whitelist.add_class('dateutil.relativedelta.relativedelta')
    safe_whitelist.add_function('time.*')
    safe_whitelist.add_instance('pytz.tzfile.UTC')
    safe_whitelist.add_function('pytz.tzinfo.DstTzInfo.localize')
    safe_whitelist.add_function('pytz.UTC.localize')
    # Collections
    safe_whitelist.add_class('collections.defaultdict')
    safe_whitelist.add_class('collections.OrderedDict')
    safe_whitelist.add_class('collections.abc.Mapping')
    safe_whitelist.add_class('collections.abc.Sized')
    safe_whitelist.add_class('collections.abc.ValuesView')
    safe_whitelist.add_class('itertools.islice')
    # Markup
    safe_whitelist.add_class('markupsafe.*')
    # Email
    safe_whitelist.add_instance('email.headerregistry._UniqueAddressHeader')
    safe_whitelist.add_instance('email.message.EmailMessage')
    # JSON
    safe_whitelist.add_instance('json.decoder.JSONDecodeError')
    # XML
    safe_whitelist.add_instance('lxml.etree._Element')
    # UUID
    safe_whitelist.add_instance('uuid.UUID')
    # Math
    safe_whitelist.add_function('math.*')
    # Base64
    safe_whitelist.add_function('base64.b64decode')
    safe_whitelist.add_function('base64.b64encode')
    safe_whitelist.add_function('base64.urlsafe_b64decode')
    safe_whitelist.add_function('base64.urlsafe_b64encode')
    # URL
    safe_whitelist.add_function('urllib.parse.quote')
    # Standard Numbers
    safe_whitelist.add_function('stdnum.pl.nip.compact')
    # Werkzeug
    safe_whitelist.add_class('werkzeug.datastructures.structures.ImmutableMultiDict')
    safe_whitelist.add_class('werkzeug.datastructures.structures.MultiDict')
    safe_whitelist.add_class('werkzeug.exceptions.BadRequest')
    safe_whitelist.add_class('werkzeug.exceptions.Forbidden')
    safe_whitelist.add_class('werkzeug.exceptions.NotFound')
    safe_whitelist.add_class('werkzeug.exceptions.RequestEntityTooLarge')
    safe_whitelist.add_class('werkzeug.exceptions.Unauthorized')
    safe_whitelist.add_instance('werkzeug.datastructures.file_storage.FileStorage')
    safe_whitelist.add_instance('werkzeug.local.LocalProxy')
    safe_whitelist.add_function('werkzeug.datastructures.structures.TypeConversionDict.*')
