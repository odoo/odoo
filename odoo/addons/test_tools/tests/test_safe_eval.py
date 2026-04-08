import ast
import inspect
from textwrap import dedent
from unittest.mock import patch

from odoo.tests.common import BaseCase, TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.misc import OrderedSet
from odoo.tools.safe_eval import (
    _BUILTINS,
    _SafeGenerator,
    UnsafeClassError,
    UnsafeFunctionError,
    UnsafeInstanceError,
    UnsafeModuleError,
    UnsafePolicy,
    const_eval,
    safe_call,
    safe_checker,
    safe_eval
)


@tagged('at_install', '-post_install')
class TestSafeEval(BaseCase):
    def test_const(self):
        # NB: True and False are names in Python 2 not consts
        expected = (1, {"a": {2.5}}, [None, u"foo"])
        actual = const_eval('(1, {"a": {2.5}}, [None, u"foo"])')
        self.assertEqual(actual, expected)
        # Test RETURN_CONST
        self.assertEqual(const_eval('10'), 10)

    def test_safe_eval_opcodes(self):
        for expr, context, expected in [
            ('[x for x in (1,2)]', {}, [1, 2]),  # LOAD_FAST_AND_CLEAR
            ('list(x for x in (1,2))', {}, [1, 2]),  # END_FOR, CALL_INTRINSIC_1
            ('v if v is None else w', {'v': False, 'w': 'foo'}, 'foo'),  # POP_JUMP_IF_NONE
            ('v if v is not None else w', {'v': None, 'w': 'foo'}, 'foo'),  # POP_JUMP_IF_NOT_NONE
            ('{a for a in (1, 2)}', {}, {1, 2}),  # RERAISE
        ]:
            self.assertEqual(safe_eval(expr, context), expected)

    def test_safe_eval_exec_opcodes(self):
        for expr, context, expected in [
            ("""
                def f(v):
                    if v:
                        x = 1
                    return x
                result = f(42)
            """, {}, 1),  # LOAD_FAST_CHECK
        ]:
            safe_eval(dedent(expr), context, mode="exec")
            self.assertEqual(context['result'], expected)

    def test_safe_eval_strips(self):
        # cpython strips spaces and tabs by deafult since 3.10
        # https://github.com/python/cpython/commit/e799aa8b92c195735f379940acd9925961ad04ec
        # but we need to strip all whitespaces
        for expr, expected in [
            # simple ascii
            ("\n 1 + 2", 3),
            ("\n\n\t 1 + 2 \n", 3),
            ("   1 + 2", 3),
            ("1 + 2   ", 3),

            # Unicode (non-ASCII spaces)
            ("\u00A01 + 2\u00A0", 3),  # nbsp
        ]:
            self.assertEqual(safe_eval(expr), expected)

    def test_runs_top_level_scope(self):
        # when we define var in top-level scope, it should become available in locals and globals
        # such that f's frame will be able to access var too.
        expr = dedent("""
        var = 1
        def f():
            return var
        f()
        """)
        safe_eval(expr, mode="exec")
        safe_eval(expr, context={}, mode="exec")

    def test_safe_eval_ctx_mutation(self):
        # simple eval also has side-effect on context
        expr = '(answer := 42)'
        context = {}
        self.assertEqual(safe_eval(expr, context), 42)
        self.assertEqual(context, {'answer': 42})

    def test_safe_eval_ctx_no_builtins(self):
        ctx = {'__builtins__': {'max': min}}
        self.assertEqual(safe_eval('max(1, 2)', ctx), 2)

    def test_01_safe_eval(self):
        """ Try a few common expressions to verify they work with safe_eval """
        expected = (1, {"a": 9 * 2}, (True, False, None))
        actual = safe_eval('(1, {"a": 9 * 2}, (True, False, None))')
        self.assertEqual(actual, expected, "Simple python expressions are not working with safe_eval")

    def test_02_literal_eval(self):
        """ Try simple literal definition to verify it works with literal_eval """
        expected = (1, {"a": 9}, (True, False, None))
        actual = ast.literal_eval('(1, {"a": 9}, (True, False, None))')
        self.assertEqual(actual, expected, "Simple python expressions are not working with literal_eval")

    def test_03_literal_eval_arithmetic(self):
        """ Try arithmetic expression in literal_eval to verify it does not work """
        with self.assertRaises(ValueError):
            ast.literal_eval('(1, {"a": 2*9}, (True, False, None))')

    def test_04_literal_eval_forbidden(self):
        """ Try forbidden expressions in literal_eval to verify they are not allowed """
        with self.assertRaises(ValueError):
            ast.literal_eval('{"a": True.__class__}')

    @mute_logger('odoo.tools.safe_eval')
    def test_05_safe_eval_forbidden(self):
        """ Try forbidden expressions in safe_eval to verify they are not allowed"""
        # no forbidden builtin expression
        with self.assertRaises(ValueError):
            safe_eval('open("/etc/passwd","r")')

        # no forbidden opcodes
        with self.assertRaises(ValueError):
            safe_eval("import odoo", mode="exec")

        # Error message shows the function's name
        with self.assertRaisesRegex(ValueError, r"forbidden opcode\(s\) in 'foo':"):
            safe_eval("def foo(x): x.bar = 2", mode="exec")

        # no dunder
        with self.assertRaises(NameError):
            safe_eval("self.__name__", {'self': self}, mode="exec")

    def test_06_safe_eval_fancy_syntax(self):
        """ Try Pythonic syntax, like comprehensions and walrus, to verify it does work"""
        safe_eval(dedent("""
            if any(x % 2 == 0 for x in range(1, 4)):
                pass  # nop
        """), mode="exec")

        safe_eval(dedent("""
            if (res := value % 2) == 0:
                res += 1
        """), mode="exec", context=(ctx := {"value": 42}))
        self.assertEqual(ctx["res"], 1)

        # LOAD_DEREF is not supported
        with self.assertRaises(ValueError):
            safe_eval(dedent("""
                def foo(a):
                    def bar(b):
                        return a + b
                    return bar
                res = foo(1)(bar)
            """), mode="exec")

        # defaults should work
        safe_eval(dedent("""
            def foo(a):
                def bar(b, a=a):
                    return a + b
                return bar
            res = foo(2)(3)
        """), mode="exec", context=(ctx := {}))
        self.assertEqual(ctx["res"], 5)

        # list comprehension
        safe_eval("res = [val + 1 for val in (1, 2)]", context=(ctx := {}), mode="exec")
        self.assertEqual(ctx["res"], [2, 3])

        # generator comprehension
        safe_eval("res = tuple(val + 1 for val in (1, 2))", context=(ctx := {}), mode="exec")
        self.assertEqual(ctx["res"], (2, 3))

        with (
            self.assertRaises(ValueError),
            mute_logger('odoo.tools.safe_eval.evaluation.runtime')  # Warning because of `async`
        ):
            # async generator comprehension
            safe_eval("res = tuple(val + 1 async for val in (1, 2))", mode="exec")

        # typing on global vars is not supported, as the generated bytecode includes dunders (__annotations__)
        with self.assertRaises(NameError):
            safe_eval("a: int", mode="exec")

        # typing functions (and vars in functions) should be working
        safe_eval(dedent("""
            def foo(a: int, b: int) -> int:
                c: int = a + b
                return c
        """), mode="exec")


@tagged('at_install', '-post_install')
class TestSafeEvalRuntime(TransactionCase):

    class UnsafeClass:  # noqa: OLS03024
        __module__ = 'odoo.unsafe_module'

        def __init__(self, *args, **kwargs): ...

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(patch(
            'odoo.tools.safe_eval.evaluation.unsafe_policy',
            lambda: UnsafePolicy.RAISE
        ))

    def setUp(self):
        super().setUp()
        self.unsafe_context = {'UnsafeClass': self.UnsafeClass}

    def test_transform_decorators(self):
        steps = []

        def make_deco(x):
            steps.append(f'make_deco_{x}')

            def deco(func):
                steps.append(f'deco_{x}')

                def wrapper(*args, **kwargs):
                    steps.append(f'wrapper_{x}')
                    return func(*args, **kwargs)

                return wrapper

            return deco

        expr = """
            @make_deco('A')
            @make_deco('B')
            def func(*args, **kwargs):
                return

            func()
        """
        safe_eval(dedent(expr), {'make_deco': make_deco}, mode='exec')
        self.assertListEqual(steps, [
            'make_deco_A', 'make_deco_B',  # Evaluation order
            'deco_B', 'deco_A',  # Wrapping order (reversed)
            'wrapper_A', 'wrapper_B',  # Evaluation order
        ])

    def test_transform_decorators_assert_name_bindings(self):
        expr = """
            @((x := func), lambda _: _)[1]
            def func(*args, **kwargs): ...
        """
        with self.assertRaisesRegex(ValueError, '^NameError'):
            safe_eval(dedent(expr), {}, mode='exec')

    def test_transform_generators(self):

        def deco(func):

            def wrapper(*args, **kwargs):
                gen = func(*args, **kwargs)
                self.assertTrue(isinstance(gen, _SafeGenerator))
                return gen

            return wrapper

        expr = """
            @deco
            def func_gen(*args, **kwargs):
                yield 1
                yield 2

                def other_gen():
                    yield 3
                    yield 4

                for value in other_gen():
                    yield value

            res = list(func_gen())
        """
        safe_eval(dedent(expr), context := {'deco': deco}, mode='exec')
        self.assertListEqual(context['res'], [1, 2, 3, 4])

    def test_transform_generators_assert_number_safe_call(self):
        expr = """
            def func_gen(*args, **kwargs):
                yield 1

            res = list(func_gen())
        """
        with patch(
            'odoo.tools.safe_eval.evaluation.safe_call',
            wraps=safe_call,
        ) as mock_safe_call:
            safe_eval(dedent(expr), {}, mode='exec')
            self.assertEqual(mock_safe_call.call_count, 1)

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_callee(self):
        expr = """
            UnsafeClass()
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_args(self):
        expr = """
            callee = lambda *args, **kwargs: ...
            callee(UnsafeClass)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_kwargs(self):
        expr = """
            callee = lambda *args, **kwargs: ...
            callee(kw=UnsafeClass)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_structure(self):
        expr = """
            callee = lambda *args, **kwargs: ...
            struct = {'a': {'b': {'c': UnsafeClass}}}
            callee(struct)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

        expr = """
            callee = lambda *args, **kwargs: ...
            struct = ['a', 'b', 'c', UnsafeClass]
            callee(struct)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_builtin_callee(self):
        expr = """
            map(UnsafeClass, ['foo'])
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

        expr = """
            filter(UnsafeClass, ['foo'])
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

        expr = """
            sorted(['foo'], key=UnsafeClass)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_callee_qweb(self):
        arch = '''
            <t t-name="template">
                <div>
                    <t t-out="UnsafeClass()"/>
                </div>
            </t>
        '''
        view = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': arch,
        })
        with self.assertRaises(UnsafeClassError):
            self.env['ir.qweb']._render(view.id, self.unsafe_context)

    def test_override_call(self):
        expr = """
            # Override in locals
            _safe_eval_call = lambda callee, *args, **kwargs: callee(*args, **kwargs)
            UnsafeClass()
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeContextError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')
        # Note that without the assert protection, we get a `RecursionError`,
        # because after transformer, the code becomes:
        # `_safe_eval_call = lambda callee, *args, **kwargs: _safe_eval_call(callee, *args, **kwargs)`

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_prevent_bare_except(self):
        expr = """
            try:
                UnsafeClass()
            except:
                pass
        """
        with self.assertRaises(SyntaxError):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_prevent_async_function(self):
        expr = """
            async def func(): ...
        """
        with self.assertRaises(SyntaxError):
            safe_eval(dedent(expr), {}, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_prevent_async_comprehension(self):
        expr = """
            (x async for x in [0])
        """
        with self.assertRaises(SyntaxError):
            safe_eval(dedent(expr), {}, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_prevent_async_for(self):
        expr = """
            async def bar():
                async for x in [0]:
                    pass
        """
        with self.assertRaises(SyntaxError):
            safe_eval(dedent(expr), {}, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_01(self):
        # Not listen events for external generator
        expr = """
            g = get_generator()
        """

        def get_generator():
            _local_var = self.UnsafeClass
            yield self.UnsafeClass

        safe_ctx = {'get_generator': get_generator}
        safe_eval(dedent(expr), safe_ctx, mode='exec')
        list(safe_ctx['g'])

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_02(self):
        # Attempt to use a dangerous object (caught in `safe_call`)
        expr = """
            g = (UnsafeClass() for _ in [0])
        """
        safe_eval(dedent(expr), self.unsafe_context, mode='exec')
        with self.assertRaises(UnsafeClassError):
            list(self.unsafe_context['g'])

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_03(self):
        # Attempt to hide a dangerous object
        expr = """
            g = (UnsafeClass for _ in [0])
            use_generator(g)
        """
        self.unsafe_context.update(
            # External logic that uses a generator
            # Regardless of the usage, the context must be checked
            use_generator=lambda g: list(g),  # noqa: PLW0108
        )
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_04(self):
        # Attempt to alter the generator's context by modifying globals
        expr = """
            d['g'] = (d['foo'] for _ in [0])
            use_generator(d)
        """

        def use_generator(d):
            d['foo'] = self.UnsafeClass
            list(d['g'])

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_05(self):
        # Attempt to alter the generator's context by modifying locals
        expr = """
            d = {}
            g = (d['foo'] for d in [d])
            use_generator(g, d)
        """

        def use_generator(g, d):
            d['foo'] = self.unsafe_context['UnsafeClass']
            return list(g)

        safe_ctx = {'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_06(self):
        # Attempt to alter the generator's context by modifying builtins
        # and shadow them in globals
        expr = """
            g = (foo for _ in [0])
            use_generator(g)
        """

        def use_generator(g):
            frame = inspect.currentframe()
            safe_call_frame = frame.f_back
            generator_frame = safe_call_frame.f_back
            generator_frame.f_builtins['foo'] = self.UnsafeClass
            list(g)

        safe_ctx = {
            'foo': '',  # Shadow builtin
            'use_generator': use_generator,
        }
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_07(self):
        # Attempt to escape unsafe context using `StopIteration` (`return`)
        expr = """
            def gen():
                return
                yield d['foo']

            d['g'] = gen()
            use_generator(d)
        """

        def use_generator(d):
            d['foo'] = self.UnsafeClass
            list(d['g'])

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_08(self):
        # Attempt to escape unsafe context using exception
        expr = """
            def gen():
                raise Exception
                yield d['foo']

            d['g'] = gen()
            try:
                use_generator(d)
            except Exception:
                pass
        """

        def use_generator(d):
            d['foo'] = self.UnsafeClass
            list(d['g'])

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_09(self):
        # Attempt to escape unsafe context using exception injection
        expr = """
            def gen():
                try:
                    yield
                except Exception:
                    yield d['foo']

            d['g'] = gen()
            use_generator(d)
        """

        def use_generator(d):
            next(d['g'])
            d['foo'] = self.UnsafeClass
            d['g'].throw(Exception())

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_10(self):
        # Attempt to escape unsafe context using intermediate yield
        expr = """
            def gen():
                yield
                yield d['foo']

            d['g'] = gen()
            use_generator(d)
        """

        def use_generator(d):
            next(d['g'])
            d['foo'] = self.UnsafeClass
            list(d['g'])

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_11(self):
        # Attempt to escape unsafe context using exceptions bypass
        expr = """
            def gen():
                try:
                    yield
                except Exception:
                    d['foo']  # Performs a variety of tasks
                    raise Exception

            d['g'] = gen()
            use_generator(d)
        """

        def use_generator(d):
            next(d['g'])
            d['foo'] = self.UnsafeClass
            d['g'].throw(Exception())

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_12(self):
        # Attempt to escape unsafe context using iterator
        expr = """
            def gen():
                yield
                yield d['foo']

            d['g'] = gen()
            use_generator(d)
        """

        def use_generator(d):
            it = iter(d['g'])
            next(it)
            d['foo'] = self.UnsafeClass
            next(it)

        safe_ctx = {'d': {}, 'use_generator': use_generator}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    @mute_logger('odoo.tools.safe_eval.evaluation.runtime')
    def test_check_generator_13(self):
        # Attempt to escape unsafe context without re-call the generator
        expr = """
            def gen():
                manipulate(d)
                yield d['foo']

            d['g'] = gen()
            use_generator(d)
        """

        def manipulate(d):
            d['foo'] = self.UnsafeClass

        def use_generator(d):
            next(d['g'])  # Return value can be used in external logic

        safe_ctx = {'d': {}, 'use_generator': use_generator, 'manipulate': manipulate}
        with self.assertRaisesRegex(ValueError, '^UnsafeClassError'):
            safe_eval(dedent(expr), safe_ctx, mode='exec')

    def test_trust_iterators(self):
        iterators = (
            iter(''),
            iter(b''),
            iter(bytearray()),
            iter({}.keys()),
            iter({}.values()),
            iter({}.items()),
            iter([]),
            iter(()),
            iter(set()),
            iter(reversed([])),
            iter(range(0)),
            iter(range(1 << 1000)),
            # No-operation iterators
            iter(zip()),
            iter(map(lambda: 0, [])),
            iter(filter(lambda: 0, [])),
            iter(sorted([])),
            iter(enumerate([])),
        )
        for iterator in iterators:
            safe_checker.check(iterator)

        # Catch hide unsafe object in trusted iterator
        # Note:
        # Some trusted classes are themselves iterators (no-operation iterators).
        # If we have an instance of these classes, we must treat them as iterators
        # rather than as ordinary instances (checking the class itself does not change).
        unsafe_iterator = enumerate((__import__,))
        with self.assertRaises(UnsafeFunctionError):
            safe_checker.check(unsafe_iterator)

    def test_trust_auto_objects(self):
        import builtins  # noqa: PLC0415
        import collections  # noqa: PLC0415
        import functools  # noqa: PLC0415
        import types  # noqa: PLC0415

        objs = (
            # classes
            builtins.object,
            builtins.bool, builtins.int, builtins.float, builtins.str,
            builtins.bytes, builtins.bytearray, builtins.memoryview,
            builtins.Exception,
            builtins.AttributeError, builtins.KeyError, builtins.TypeError,
            builtins.UnboundLocalError, builtins.ValueError, builtins.ZeroDivisionError,
            builtins.enumerate, builtins.filter, builtins.map, builtins.range,
            builtins.reversed, builtins.zip,
            builtins.dict,
            builtins.list, builtins.tuple, builtins.set, builtins.frozenset,
            types.MappingProxyType,
            collections.defaultdict, collections.OrderedDict,
            # classes in tools
            OrderedSet,
            # functions
            builtins.abs, builtins.divmod, builtins.max, builtins.min,
            builtins.round, builtins.sum,
            builtins.chr, builtins.ord, builtins.repr,
            builtins.all, builtins.any, builtins.len, builtins.sorted,
            builtins.hasattr, builtins.isinstance,
            functools.reduce,
        )
        for obj in objs:
            safe_checker.check(obj)

        # Ensure controlled builtins are trusted
        for obj in _BUILTINS.values():
            safe_checker.check(obj)

    def test_trust_wrapped_modules(self):
        # Modules is not verified
        import datetime  # noqa: PLC0415
        import dateutil  # noqa: PLC0415
        import dateutil.parser  # noqa: PLC0415
        import dateutil.relativedelta  # noqa: PLC0415
        import dateutil.rrule  # noqa: PLC0415
        import dateutil.tz  # noqa: PLC0415
        import json  # noqa: PLC0415
        import time  # noqa: PLC0415

        modules = (
            datetime,
            dateutil,
            dateutil.parser,
            dateutil.relativedelta,
            dateutil.rrule,
            dateutil.tz,
            json,
            time,
        )
        for module in modules:
            with self.assertRaises(UnsafeModuleError):
                safe_checker.check(module)

        # Only wrapped modules can be used
        import odoo.tools.safe_eval as safe_eval  # noqa: PLC0415

        modules = (
            safe_eval.datetime,
            safe_eval.dateutil,
            safe_eval.dateutil.parser,
            safe_eval.dateutil.relativedelta,
            safe_eval.dateutil.rrule,
            safe_eval.dateutil.tz,
            safe_eval.json,
            safe_eval.time,
        )
        for module in modules:
            safe_checker.check(module)

        # Objects of authorised modules must be trusted
        objs = (
            datetime.date, datetime.datetime, datetime.time, datetime.timedelta,
            datetime.timezone, datetime.tzinfo,
            dateutil.tz.UTC, dateutil.tz.tzutc,
            dateutil.parser.isoparse, dateutil.parser.parse,
            dateutil.relativedelta.relativedelta,
            dateutil.rrule.rrule, dateutil.rrule.rruleset, dateutil.rrule.rrulestr,
            json.loads, json.dumps,
            time.time, time.strptime, time.strftime, time.sleep,
        )
        for obj in objs:
            safe_checker.check(obj)

        # Specific test for monkeypatched `ZoneInfo` class
        with self.assertRaises(UnsafeInstanceError):
            safe_checker.check(dateutil.tz.gettz)
        safe_checker.check(safe_eval.dateutil.tz.gettz)

        # Specific test for import
        with self.assertRaises(UnsafeFunctionError):
            safe_checker.check(__import__)
        safe_checker.check(safe_eval._import)

    def test_prevent_bypass_module(self):
        from collections import deque  # noqa: PLC0415

        unsafe_func = deque().append
        self.assertFalse(unsafe_func.__module__)

        with self.assertRaises(UnsafeFunctionError):
            safe_checker.check(deque().append)
