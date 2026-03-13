import ast

from textwrap import dedent
from unittest.mock import patch

from odoo import Command
from odoo.tests.common import tagged, BaseCase, TransactionCase
from odoo.tools import mute_logger
from odoo.tools.safe_eval import (
    const_eval,
    expr_eval,
    safe_eval,
    UnsafeObjectError,
    UnsafePolicy,
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

    def test_expr(self):
        # NB: True and False are names in Python 2 not consts
        expected = 3 * 4
        actual = expr_eval('3 * 4')
        self.assertEqual(actual, expected)

    def test_expr_eval_opcodes(self):
        for expr, expected in [
            ('3', 3),  # RETURN_CONST
            ('[1,2,3,4][1:3]', [2, 3]),  # BINARY_SLICE
        ]:
            self.assertEqual(expr_eval(expr), expected)

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
    def test_05_safe_eval_forbiddon(self):
        """ Try forbidden expressions in safe_eval to verify they are not allowed"""
        # no forbidden builtin expression
        with self.assertRaises(ValueError):
            safe_eval('open("/etc/passwd","r")')

        # no forbidden opcodes
        with self.assertRaises(ValueError):
            safe_eval("import odoo", mode="exec")

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

        with self.assertRaises(ValueError):
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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(patch(
            'odoo.tools.safe_eval.unsafe_policy',
            lambda: UnsafePolicy.RAISE
        ))

        class UnsafeClass:
            __module__ = 'odoo.unsafe_module'

            def __init__(self, *args, **kwargs): ...

        cls.unsafe_context = {'UnsafeClass': UnsafeClass}

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

    @mute_logger('odoo.tools.safe_eval.runtime')
    def test_check_callee(self):
        expr = """
            UnsafeClass()
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.runtime')
    def test_check_args(self):
        expr = """
            callee = lambda *args, **kwargs: ...
            callee(UnsafeClass)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.runtime')
    def test_check_kwargs(self):
        expr = """
            callee = lambda *args, **kwargs: ...
            callee(kw=UnsafeClass)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.runtime')
    def test_check_structure(self):
        expr = """
            callee = lambda *args, **kwargs: ...
            struct = {'a': {'b': {'c': UnsafeClass}}}
            callee(struct)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

        expr = """
            callee = lambda *args, **kwargs: ...
            struct = ['a', 'b', 'c', UnsafeClass]
            callee(struct)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.runtime')
    def test_check_builtin_callee(self):
        expr = """
            map(UnsafeClass, ['foo'])
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

        expr = """
            filter(UnsafeClass, ['foo'])
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

        expr = """
            sorted(['foo'], key=UnsafeClass)
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeObjectError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')

    @mute_logger('odoo.tools.safe_eval.runtime')
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
        with self.assertRaises(UnsafeObjectError):
            self.env['ir.qweb']._render(view.id, self.unsafe_context)

    def test_override_call(self):
        expr = """
            # Override in locals
            _save_eval_call = lambda callee, *args, **kwargs: callee(*args, **kwargs)
            UnsafeClass()
        """
        with self.assertRaisesRegex(ValueError, '^UnsafeContextError'):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')
        # Note that without the assert protection, we get a `RecursionError`,
        # because after transformer, the code becomes:
        # `_save_eval_call = lambda callee, *args, **kwargs: _save_eval_call(callee, *args, **kwargs)`

    @mute_logger('odoo.tools.safe_eval.runtime')
    def test_prevent_bare_except(self):
        expr = """
            try:
                UnsafeClass()
            except:
                pass
        """
        with self.assertRaises(SyntaxError):
            safe_eval(dedent(expr), self.unsafe_context, mode='exec')
