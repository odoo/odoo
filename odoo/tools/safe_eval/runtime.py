"""
Runtime analysis for arbitrary code evaluated with the `evaluation.py` module.

- `safe_transformer`:
    A specialized `ast.NodeTransformer` that rewrites the source.

- `safe_checker`:
    The logic engine responsible for inspecting objects at runtime.

- `safe_whitelist`:
    A collection of trusted objects (defined as regex and object references).
"""
import ast
import functools
import logging
import os
import re
import sys
import typing
from collections import OrderedDict, defaultdict
from contextvars import ContextVar
from enum import IntEnum, auto
from json.encoder import c_make_encoder  # noqa: OLS02001
from types import (
    BuiltinMethodType,
    ClassMethodDescriptorType,
    CodeType,
    FunctionType,
    GeneratorType,
    GetSetDescriptorType,
    MappingProxyType,
    MemberDescriptorType,
    MethodDescriptorType,
    MethodType,
    ModuleType,
    NoneType,
    WrapperDescriptorType,
    _GeneratorWrapper,  # noqa: OLS02001
)
from weakref import WeakKeyDictionary

from ..config import config
from ..func import lazy
from ..misc import OrderedSet

__all__ = [
    'safe_checker',
    'safe_transform',
    'safe_whitelist',
    'unsafe_policy',
]

_logger_runtime = logging.getLogger(__name__)


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


class UnsafeError(BaseException):
    """
    Base class for exceptions triggered by unsafe operations.

    Ideally used as a high-level handler to catch exceptions related
    to unsafe errors.
    Since this inherits from `BaseException`, it will bypass standard
    `except Exception:` blocks.
    """


class UnsafeContextError(UnsafeError):
    """ Exception raised when the evaluation context is unsafe. """


class UnsafeObjectError(UnsafeError):
    """ Exception raised when an object is unsafe. """


class UnsafeModuleError(UnsafeObjectError):

    def __init__(self, obj):
        super().__init__(f'Unsafe module access: {obj!r}')


class UnsafeClassError(UnsafeObjectError):

    def __init__(self, obj):
        obj_path = safe_whitelist.get_full_path(obj)
        super().__init__(f'Unsafe class access: {obj!r} (path: {obj_path})')


class UnsafeInstanceError(UnsafeObjectError):

    def __init__(self, obj):
        obj_path = safe_whitelist.get_full_path(type(obj))
        super().__init__(
            f'Unsafe instance access: {obj!r} (type: {type(obj)!r}, path: {obj_path})',
        )


class UnsafeFunctionError(UnsafeObjectError):

    def __init__(self, obj):
        obj_path = safe_whitelist.get_full_path(obj)
        super().__init__(
            f'Unsafe function access: {obj!r} (type: {type(obj)!r}, path: {obj_path})',
        )


def handle_unsafe_error(error):
    _logger_runtime.warning(error)
    if unsafe_policy() is UnsafePolicy.RAISE:
        raise error
    if unsafe_policy() is UnsafePolicy.TERMINATE:
        os._exit(1)


is_gen_ctx: ContextVar[bool] = ContextVar('is_gen_ctx', default=False)


class _SafeTransformer(ast.NodeTransformer):
    """
    Code transformer that wraps calls with :func:`_safe_eval_call` in
    order to check that the arguments are "safe".
    """

    # In Qweb, we use the transformer to modify the python expression.
    # The ast will not be compiled, but instead "unparsed" in the transpiled template.
    # The expression will be used later and therefore re-parsed.
    # It is therefore necessary for the identifiers to be valid.

    CALL_ID = '_safe_eval_call'
    DECO_ID = '_safe_eval_deco'
    GEN_FUNC_ID = '_safe_eval_gen_func'
    GEN_ITER_ID = '_safe_eval_gen_iter'

    def visit_Call(self, node):
        """
        Transforms:
            func(*args, **kwargs)

        Into:
            _safe_eval_call(func, *args, **kwargs)
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
            @_safe_eval_deco(decorator_A)
            @_safe_eval_deco(decorator_B)
            def func():
                pass

        Note:
            If the function produces a generator, a decorator is added to wrap
            the result with `_safe_eval_gen_func`.
        """
        token = is_gen_ctx.set(False)
        try:
            self.generic_visit(node)
            is_gen = is_gen_ctx.get()
        finally:
            is_gen_ctx.reset(token)

        if not node.decorator_list and not is_gen:
            return node

        new_decorators = []

        for decorator in node.decorator_list:
            wrapped_decorator = ast.Call(
                func=ast.Name(id=self.DECO_ID, ctx=ast.Load()),
                args=[decorator],
                keywords=[],
            )
            ast.copy_location(wrapped_decorator, decorator)
            ast.copy_location(wrapped_decorator.func, decorator)
            new_decorators.append(wrapped_decorator)

        if is_gen:
            gen_func_wrapper = ast.Name(id=self.GEN_FUNC_ID, ctx=ast.Load())
            ast.copy_location(gen_func_wrapper, node)
            new_decorators.append(gen_func_wrapper)

        node.decorator_list = new_decorators

        return node

    def visit_Yield(self, node):
        """ Set parent function definition as a generator function """
        is_gen_ctx.set(True)
        return self.generic_visit(node)

    visit_YieldFrom = visit_Yield

    def visit_GeneratorExp(self, node):
        """
        Transforms:
            (_ for _ in [])

        Into:
            _safe_eval_gen_iter((_ for _ in []))
        """
        self.generic_visit(node)
        call = ast.Call(
            func=ast.Name(id=self.GEN_ITER_ID, ctx=ast.Load()),
            args=[node],
            keywords=[],
        )
        ast.copy_location(call, node)
        ast.copy_location(call.func, node)
        return call

    def visit_Try(self, node):
        """ Ensure no bare except is used """
        self.generic_visit(node)

        for handler in node.handlers:
            if not handler.type:
                _logger_runtime.warning(
                    'Use blind except (`except Exception:`) instead of bare except',
                )
                if unsafe_policy() >= UnsafePolicy.RAISE:
                    raise SyntaxError('You cannot use bare except, use `except Exception:`')

        return node

    def visit_AsyncFunctionDef(self, node):
        # Prevent the use of `AsyncFor` node
        _logger_runtime.warning(
            'Asynchronous function should not be used',
        )
        if unsafe_policy() >= UnsafePolicy.RAISE:
            raise SyntaxError('You cannot use asynchronous function')

        return self.visit_FunctionDef(node)

    def visit_comprehension(self, node):
        """ Ensure async is not used """
        self.generic_visit(node)

        if node.is_async:
            _logger_runtime.warning(
                'Asynchronous comprehension should not be used',
            )
            if unsafe_policy() >= UnsafePolicy.RAISE:
                raise SyntaxError('You cannot use asynchronous comprehension')

        return node


encoder_ctx = ContextVar('encoder_ctx')


class _SafeChecker:
    """
    Callable object that checks whether a value is considered "safe".
    It does so by using on a JSON encoder, for which one can add type-specific hooks.
    An empty hook simply considers the given type as completely safe,
    while other hooks may check a value and return values to be recursively checked.
    """

    MAPPINGS = frozenset((dict, defaultdict, OrderedDict, MappingProxyType))
    SEQUENCES = frozenset((list, tuple, set, frozenset, OrderedSet))
    ITERATORS = frozenset((
        enumerate, filter, map, range, reversed, zip,
        type(iter('')), type(iter(b'')), type(iter(bytearray())),
        type(iter([])), type(iter(())), type(iter(set())),
        type(iter(reversed([]))),
        type(iter({}.keys())), type(iter({}.values())), type(iter({}.items())),
        type(iter(range(0))), type(iter(range(1 << 1000))),  # `range_iterator` vs `longrange_iterator`
    ))

    def __init__(self):
        self.__hooks: WeakKeyDictionary[type, typing.Callable | None] = WeakKeyDictionary()
        self._hook_class = safe_whitelist.check_class
        self._hook_instance = safe_whitelist.check_instance
        self._hook_function = safe_whitelist.check_function

        # Primary hooks
        self.add_hook(ModuleType, self._hook_module)
        self.add_hook(type, self._hook_class)
        self.add_hook(FunctionType, self._hook_function)
        # Secondary hooks
        self.add_hook(MethodType, self._hook_method)
        self.add_hook(BuiltinMethodType, self._hook_builtin_method)  # is `BuiltinFunctionType`
        self.add_hook(MethodDescriptorType, self._hook_descriptor)
        self.add_hook(MemberDescriptorType, self._hook_descriptor)
        self.add_hook(GetSetDescriptorType, self._hook_descriptor)
        self.add_hook(ClassMethodDescriptorType, self._hook_class_method_descriptor)
        self.add_hook(WrapperDescriptorType, self._hook_wrapper_descriptor)
        # Serialization hooks
        for t in _SafeWhitelist.TRUSTED_CLASSES: self.add_hook(t, None)  # Optimization to save time when serializing these types  # noqa: E701
        # /!\ optimizations can be overwritten
        for t in self.SEQUENCES: self.add_hook(t, list)  # noqa: E701
        for t in self.MAPPINGS: self.add_hook(t, dict)  # noqa: E701
        for t in self.ITERATORS: self.add_hook(t, self._hook_iterator)  # noqa: E701
        self.add_hook(GeneratorType, None)
        self.add_hook(_SafeGenerator, None)
        self.add_hook(functools.partial, self._hook_partial)
        self.add_hook(lazy, self._hook_lazy)
        d = {}
        self.add_hook(type(d.items()), list)
        self.add_hook(type(d.keys()), list)
        self.add_hook(type(d.values()), list)
        d = OrderedDict()
        self.add_hook(type(d.items()), list)
        self.add_hook(type(d.keys()), list)
        self.add_hook(type(d.values()), list)

    def add_hook(self, type_: type, hook: typing.Callable | None = None) -> None:
        self.__hooks[type_] = hook or self._hook_nop

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
            return self.__hooks[t_obj](obj)
        except KeyError:
            if isinstance(obj, type):
                hook = self._hook_class
            else:
                hook = self._hook_instance
            self.__hooks[t_obj] = hook
            return hook(obj)

    def _hook_nop(self, obj):
        return None

    def _hook_module(self, obj):
        raise UnsafeModuleError(obj)

    def _hook_method(self, obj):
        bound_obj = obj.__self__
        try:
            return (self._hook_class if isinstance(bound_obj, type) else self._hook_instance)(bound_obj)
        except UnsafeObjectError:
            return self._hook_function(obj)

    def _hook_builtin_method(self, obj):
        bound_obj = obj.__self__
        # Try trusted with bound object (which can be a module)
        if isinstance(bound_obj, ModuleType):
            return self._hook_function(obj)
        try:
            return (self._hook_class if isinstance(bound_obj, type) else self._hook_instance)(bound_obj)
        except UnsafeObjectError:
            return self._hook_function(obj)

    def _hook_descriptor(self, obj):
        try:
            return self._hook_class(obj.__objclass__)
        except UnsafeObjectError:
            return self._hook_function(obj)

    def _hook_class_method_descriptor(self, obj):
        # C-level class methods, used for protocol hooks
        # These are effectively "only" exposed as dunder methods
        raise UnsafeFunctionError(obj)

    def _hook_wrapper_descriptor(self, obj):
        # C-level slot wrappers (e.g. __add__, __len__)
        # These are always exposed as dunder methods
        raise UnsafeFunctionError(obj)

    def _hook_iterator(self, obj):
        return obj.__reduce__()

    def _hook_partial(self, obj):
        return (obj.func, obj.args, obj.keywords)

    def _hook_lazy(self, obj):
        if getattr(obj, '_func', None) is None:
            return obj._cached_value
        return (obj._func, obj._args, obj._kwargs)


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
    TRUSTED_CLASSES = frozenset((
        # basic types
        object,
        NoneType, bool, int, float, str, bytes, bytearray, memoryview,
        # errors
        Exception,
        AttributeError, KeyError, TypeError, UnboundLocalError, ValueError,
        ZeroDivisionError,
        # iterators and generators
        enumerate, filter, map, range, reversed, zip,
        *_SafeChecker.MAPPINGS, *_SafeChecker.SEQUENCES,
    ))
    TRUSTED_FUNCTIONS = frozenset((
        # math and numbers
        abs, divmod, max, min, round, sum,
        # string and conversion
        chr, ord, repr,
        # collections and iterables
        all, any, len, sorted, iter,
        # introspection and type checking
        hasattr, isinstance,
        # others
        functools.reduce,
    ))

    @staticmethod
    def get_full_path(cls_obj: type) -> str:
        try:
            qualname = cls_obj.__qualname__
        except (AttributeError, RuntimeError):
            qualname = ''

        if module := getattr(cls_obj, '__module__', None):
            if (
                module in sys.modules or
                module == 'odoo.tools.safe_eval.evaluation.<evaluated_code>'
            ):
                return f'{module}.{qualname}'.strip('.')

            # The object can be defined in a module which is not register,
            # for example via `load_script`. It is the case for upgrade.
            if code := getattr(cls_obj, '__code__', None):
                file_path = os.path.abspath(code.co_filename)
                for upgrade_path in config['upgrade_path']:
                    upgrade_path = os.path.abspath(upgrade_path)
                    if os.path.commonpath([file_path, upgrade_path]) == upgrade_path:
                        return f'odoo.upgrade.{qualname}'.strip('.')

        if type(cls_obj) is ModuleType:
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

    def check_class(self, obj) -> None:
        if (
            obj not in self.TRUSTED_CLASSES and
            not self._re_class.fullmatch(self.get_full_path(obj))
        ):
            raise UnsafeClassError(obj)

    def check_instance(self, obj) -> None:
        t_obj = type(obj)
        if (
            t_obj not in self.TRUSTED_CLASSES and
            not self._re_instance.fullmatch(self.get_full_path(t_obj))
        ):
            raise UnsafeInstanceError(obj)

    def check_function(self, obj) -> None:
        if (
            obj not in self.TRUSTED_FUNCTIONS and
            not self._re_function.fullmatch(self.get_full_path(obj))
        ):
            raise UnsafeFunctionError(obj)


class _SafeGenerator(_GeneratorWrapper):  # noqa: OLS01002

    def send(self, *args):
        assert_safe_context(self)
        try:
            return super().send(*args)
        finally:
            assert_safe_context(self)

    def throw(self, *args):
        assert_safe_context(self)
        try:
            return super().throw(*args)
        finally:
            assert_safe_context(self)

    def close(self, *args):
        assert_safe_context(self)
        try:
            return super().close(*args)
        finally:
            assert_safe_context(self)

    def __next__(self, *args):
        assert_safe_context(self)
        try:
            return super().__next__(*args)
        finally:
            assert_safe_context(self)

    def __iter__(self, *args):
        assert_safe_context(self)
        return self  # Not use `super`, as it leaks the wrapped generator

    __await__ = __iter__


def safe_gen_wrapper(func):

    def _wrapper(*args, **kwargs):
        gen = safe_call(func, *args, **kwargs)
        return _SafeGenerator(gen)

    return _wrapper


def safe_call(callee, /, *args, **kwargs):
    """ Ensure objects used for the call are safe """
    try:
        safe_checker.check((callee, args, kwargs))
    except UnsafeError as e:
        handle_unsafe_error(e)
    return callee(*args, **kwargs)


def safe_call_deco(func):
    """ Ensure call `safe_call` for decorators """
    return lambda *args, **kwargs: safe_call(func, *args, **kwargs)


safe_transformer = _SafeTransformer()
safe_transform = safe_transformer.visit
safe_whitelist = _SafeWhitelist()
safe_checker = _SafeChecker()

safe_whitelist.TRUSTED_CLASSES |= {_SafeGenerator}
safe_whitelist.TRUSTED_FUNCTIONS |= {safe_call, safe_call_deco, safe_gen_wrapper}

# ==========
# Monitoring
# ==========


def monitoring_call(code, instruction_offset, callee, arg0):
    """ Ensure `_MONITORING_BUILTINS` are not overridden """
    if callee in (safe_call, safe_call_deco, _SafeGenerator, safe_gen_wrapper):
        return

    frame = sys._getframe(1)
    for identifier, expected in _MONITORING_BUILTINS.items():
        if (
            (identifier in frame.f_locals and frame.f_locals[identifier] is not expected) or
            (identifier in frame.f_globals and frame.f_globals[identifier] is not expected) or
            frame.f_builtins[identifier] is not expected
        ):
            raise UnsafeContextError(f'{identifier} is overridden')


def assert_safe_context(gen: GeneratorType) -> None:
    """ Ensure mutating context of generator is safe """
    if not (frame := gen.gi_frame):
        return  # If there is no frame, the generator is finished
    objs = list(frame.f_locals.values())
    for name in gen.gi_code.co_names:
        if name in frame.f_globals:
            objs.append(frame.f_globals[name])
        if name in frame.f_builtins:
            objs.append(frame.f_builtins[name])
    # The use of freevars (closures) is not allowed
    try:
        safe_checker.check(objs)
    except UnsafeObjectError as e:
        handle_unsafe_error(e)


_MONITORING_BUILTINS = {
    safe_transformer.CALL_ID: safe_call,
    safe_transformer.DECO_ID: safe_call_deco,
    safe_transformer.GEN_FUNC_ID: safe_gen_wrapper,
    safe_transformer.GEN_ITER_ID: _SafeGenerator,
}

EVENTS = sys.monitoring.events
TOOL_ID = 4  # Not prevent other tools from using "official IDs"
sys.monitoring.use_tool_id(TOOL_ID, 'ODOO_UNSAFE_POLICY_TOOL')
sys.monitoring.register_callback(TOOL_ID, EVENTS.CALL, monitoring_call)


def add_monitoring(code):
    codes = [code]
    while codes:
        code = codes.pop()
        sys.monitoring.set_local_events(TOOL_ID, code, EVENTS.CALL)
        codes.extend(const for const in code.co_consts if isinstance(const, CodeType))


@functools.cache
def _initialize_safe_whitelist():
    # Custom functions
    safe_whitelist.add_function('odoo.tools.safe_eval.evaluation.<evaluated_code>.*')
    # Generators wrapper
    safe_whitelist.add_function('odoo.tools.safe_eval.runtime.safe_gen_wrapper.<locals>._wrapper')
    # Wrapped modules
    safe_whitelist.add_class('datetime.date')
    safe_whitelist.add_class('datetime.datetime')
    safe_whitelist.add_class('datetime.time')
    safe_whitelist.add_class('datetime.timedelta')
    safe_whitelist.add_class('datetime.timezone')
    safe_whitelist.add_class('datetime.tzinfo')
    safe_whitelist.add_class('dateutil.tz.tz.tzutc')
    safe_whitelist.add_function('dateutil.parser.isoparser.isoparser.isoparse')
    safe_whitelist.add_function('dateutil.parser._parser.parse')
    safe_whitelist.add_class('dateutil.relativedelta.relativedelta')
    safe_whitelist.add_class('dateutil.rrule.rrule')
    safe_whitelist.add_class('dateutil.rrule.rruleset')
    safe_whitelist.add_instance('dateutil.rrule._rrulestr')
    safe_whitelist.add_function('json.dumps')
    safe_whitelist.add_function('json.loads')
    safe_whitelist.add_function('time.time')
    safe_whitelist.add_function('time.strptime')
    safe_whitelist.add_function('time.strftime')
    safe_whitelist.add_function('time.sleep')
    # Monkey patches
    safe_whitelist.add_class('odoo._monkeypatches.zoneinfo.ZoneInfo')
    safe_whitelist.add_function('odoo._monkeypatches.*')
    # Core
    safe_whitelist.add_class('odoo.addons.*')  # TODO: Restrict addons
    safe_whitelist.add_function('odoo.addons.*')  # TODO: remove with restrict addons
    safe_whitelist.add_class('odoo.upgrade.*')
    safe_whitelist.add_function('odoo.upgrade.*')
    safe_whitelist.add_class('odoo.orm.domains.*')
    safe_whitelist.add_class('odoo.orm.fields.*')
    safe_whitelist.add_class('odoo.orm.fields_binary.*')
    safe_whitelist.add_class('odoo.orm.fields_properties.*')
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
    safe_whitelist.add_function('werkzeug.datastructures.headers.Headers.get')
    safe_whitelist.add_function('werkzeug.datastructures.structures.TypeConversionDict.*')
