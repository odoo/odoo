# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import datetime
import sys
import os
import time

from inspect import cleandoc
from markupsafe import Markup
from unittest.mock import patch

from odoo import Command
from odoo.tests.common import TransactionCase, BaseCase
from odoo.tools import mute_logger

from odoo.tools.safe_eval import (
    safe_eval,
    const_eval,
    expr_eval,
    _prepare_environment,
    allow_type,
    CodeChecker,
    SafeWrapper,
    unsafe_eval,
    _AST_MATH_NODES,
    _AST_ALLOWED_NODES
)


class TestSafeEval(BaseCase):
    maxDiff = None

    def setUp(self):
        self.code_checker = CodeChecker(_AST_ALLOWED_NODES)

    def inject(self, expr):
        return ast.unparse(self.code_checker.visit(ast.parse(expr)))

    def test_const(self):
        # NB: True and False are names in Python 2 not consts
        expected = (1, {"a": {2.5}}, [None, u"foo"])
        actual = const_eval('(1, {"a": {2.5}}, [None, u"foo"])')
        self.assertEqual(actual, expected)

    def test_expr(self):
        # NB: True and False are names in Python 2 not consts
        expected = 3 * 4
        actual = expr_eval('3 * 4')
        self.assertEqual(actual, expected)

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
        """ Try forbidden expressions in safe_eval to verify they are not allowed """
        # no forbidden builtin expression
        with self.assertRaisesRegex(ValueError, r"unsafe object: <built-in function open*"):
            safe_eval('open("/etc/passwd","r")', mode="exec", globals_dict={"open": open})

        # no forbidden opcodes
        with self.assertRaises(SyntaxError):
            safe_eval("import odoo", mode="exec")

        # no dunder
        with self.assertRaises(NameError):
            safe_eval("self.__name__", {'self': self}, mode="exec")

    def test_06_call_checker_injection(self):
        """ Test that the call_checker is injected into the code"""

        self.assertEqual(
            self.inject("foo(bar, baz=qux)"),
            "__call_checker(__func=foo, __args=[bar], __kwargs={'baz': qux})"
        )

        self.assertEqual(
            self.inject("foo.bar(baz, qux=quux)"),
            "__call_checker(__func=__SafeWrapper(__obj=__type_checker(__obj=foo), __type_checker=__type_checker).bar, __args=[baz], __kwargs={'qux': quux})"
        )

        self.assertEqual(
            self.inject("foo()"),
            "__call_checker(__func=foo, __args=[], __kwargs={})",
        )

        with self.assertRaisesRegex(NameError, r"unsafe node: __call_checker \(dunder name\)"):
            self.inject("__call_checker(foo, bar, baz=qux)")

        with self.assertRaisesRegex(NameError, r"unsafe node: __call_checker \(dunder name\)"):
            self.inject("foo(__call_checker, bar, baz=qux)")

        with self.assertRaisesRegex(NameError, r"unsafe node: __call_checker \(dunder name\)"):
            self.inject("foo(bar, __call_checker=baz, qux=quux)")

        with self.assertRaisesRegex(NameError, r"unsafe node: __call_checker \(dunder name\)"):
            self.inject("foo(bar, baz=__call_checker, qux=quux)")

    def test_07_attr_injection(self):
        self.assertEqual(
            self.inject("foo.bar"),
            "__SafeWrapper(__obj=__type_checker(__obj=foo), __type_checker=__type_checker).bar",
        )

        self.assertEqual(
            self.inject("foo.bar.baz"),
            "__SafeWrapper(__obj=__type_checker(__obj=__SafeWrapper(__obj=__type_checker(__obj=foo), __type_checker=__type_checker).bar), __type_checker=__type_checker).baz"
        )

        self.assertEqual(
            self.inject("foo.bar(baz)"),
            "__call_checker(__func=__SafeWrapper(__obj=__type_checker(__obj=foo), __type_checker=__type_checker).bar, __args=[baz], __kwargs={})"
        )

        self.assertEqual(
            self.inject("foo.bar(baz, qux=quux.quuz)"),
            "__call_checker(__func=__SafeWrapper(__obj=__type_checker(__obj=foo), __type_checker=__type_checker).bar, __args=[baz], __kwargs={'qux': __SafeWrapper(__obj=__type_checker(__obj=quux), __type_checker=__type_checker).quuz})"
        )

    def test_10_subscript(self):
        lst = [
            0, sys
        ]

        dico = {
            "a": "b",
            "c": sys,
            sys: lambda _: 1
        }

        safe_eval("lst[0]", globals_dict={"lst": lst})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <module \'sys\'"):
            safe_eval("lst[1]", globals_dict={"lst": lst})

        safe_eval("dico['a']", globals_dict={"dico": dico})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <module \'sys\'"):
            safe_eval("dico['c']", globals_dict={"dico": dico})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <module \'sys\'*"):
            safe_eval("dico[sys]", globals_dict={"dico": dico, "sys": sys})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <module \'sys\'*"):
            safe_eval("a, = get_sys()[1:]", mode="exec", globals_dict={"get_sys": lambda: [sys, sys]})

    def test_08_format_should_be_denied(self):
        # format is rforbidden on strings
        # because it can be used to leak data through dunders
        with self.assertRaisesRegex(ValueError, "unsafe attribute access:*"):
            safe_eval(cleandoc(
                """
                fmt = "Hello {name}"
                fmt.format(name="World")
                """
            ), mode="exec")

        with self.assertRaisesRegex(ValueError, "unsafe attribute access:*"):
            safe_eval(cleandoc(
                """
                fmt = "Hello {}"
                fmt.format("World")
                """
            ), mode="exec")

        with self.assertRaisesRegex(ValueError, "unsafe attribute access:*"):
            safe_eval(cleandoc(
                """
                fmt = "Hello {name}"
                fmt.format_map({"name": "World"})
                """
            ), mode="exec")

        with self.assertRaisesRegex(ValueError, "unsafe attribute access:*"):
            safe_eval(cleandoc(
                """
                Markup('Hello {}'.format('World'))
                """
            ), mode="exec", globals_dict={"Markup": Markup})

        with self.assertRaisesRegex(ValueError, "unsafe attribute access:*"):
            safe_eval(cleandoc(
                """
                str.format("Hello {}", "World")
                """
            ), mode="exec", globals_dict={"Markup": Markup})

        # Those type of format are allowed
        safe_eval(cleandoc(
            """
            fmt = "Hello %s"
            fmt % "World"
            """
        ), mode="exec")
        safe_eval(cleandoc(
            """
            fmt = f"Hello {'World'}"
            """
        ), mode="exec")

        # Check that format method on other objects is allowed
        class SomeObject:
            def format(*args, **kwargs):
                ...

        code = cleandoc(
            """
            fmt = SomeObject()
            fmt.format(name="World")
            """
        )

        safe_eval(code, globals_dict={"SomeObject": SomeObject}, mode="exec", sandbox_types=(SomeObject,))

    def test_09_use_of_denied_ast_nodes(self):
        # Case 1: use of ast.Call with safe_eval in "math" mode
        with self.assertRaisesRegex(SyntaxError, r"unsafe node: Call \(node not allowed\)"):
            safe_eval("foo()", ast_subset=_AST_MATH_NODES | {ast.Load}, globals_dict={"foo": lambda: 1}, mode="exec")

        # Case 2: Forcing ast.ImportFrom inside of the sandbox
        with self.assertRaisesRegex(ValueError, r"unsafe node: ImportFrom \(node not allowed\)"):
            safe_eval("from random import randint", ast_subset=_AST_ALLOWED_NODES | {ast.ImportFrom})

    def test_10_wrap_module(self):
        # Everything in a module is visible, but only the allowed objects are accessible
        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval("datetime.sys", globals_dict={"datetime": datetime}, mode="eval")

    def test_14_deny_attribute_modifications(self):
        class Foo:
            def __init__(self):
                self.bar = 0

        with self.assertRaisesRegex(ValueError, "unsafe attribute assignation"):
            safe_eval("foo.bar = 1", globals_dict={"foo": Foo()}, mode="exec", sandbox_instances=(Foo,))

        with self.assertRaisesRegex(ValueError, "unsafe attribute assignation: bar"):
            safe_eval("foo.bar += 1", globals_dict={"foo": Foo()}, mode="exec", sandbox_instances=(Foo,))

        with self.assertRaisesRegex(ValueError, "unsafe attribute assignation: bar"):
            safe_eval("for foo.bar in range(10): ...", globals_dict={"foo": Foo()}, mode="exec",
                      sandbox_instances=(Foo,))

        with self.assertRaisesRegex(ValueError, "unsafe attribute assignation: bar"):
            safe_eval("for (foo.bar, b) in [(1, 2)]: ...", globals_dict={"foo": Foo()}, mode="exec",
                      sandbox_instances=(Foo,))

        with self.assertRaisesRegex(ValueError, "unsafe attribute assignation: bar"):
            safe_eval("list((0 for foo.bar in range(10)))", globals_dict={"foo": Foo()}, sandbox_instances=(Foo,),
                      mode="exec")

        # For internal use, CheckerWrapper allows setattr on dunders, it should be forbidden from inside of the sandbox
        # It will be caught by the explore_Name method of the CodeChecker
        with self.assertRaisesRegex(NameError, r"unsafe node: __bar \(dunder name\)"):
            safe_eval("foo.__bar = 1", globals_dict={"foo": Foo()}, mode="exec", sandbox_instances=(Foo,))

        with self.assertRaisesRegex(NameError, r"unsafe node: __bar \(dunder name\)"):
            safe_eval("foo.__bar += 1", globals_dict={"foo": Foo()}, mode="exec", sandbox_instances=(Foo,))

        with self.assertRaisesRegex(NameError, r"unsafe node: __bar \(dunder name\)"):
            safe_eval("for foo.__bar in range(10): ...", globals_dict={"foo": Foo()}, mode="exec",
                      sandbox_instances=(Foo,))

        with self.assertRaisesRegex(NameError, r"unsafe node: __bar \(dunder name\)"):
            safe_eval("for (foo.__bar, b) in [(1, 2)]: ...", globals_dict={"foo": Foo()}, mode="exec",
                      sandbox_instances=(Foo,))

        safe_eval("for (a, b) in enumerate(range(10)): ...", mode="exec")
        safe_eval("(a for (a, b) in enumerate(range(10)))", mode="exec")

        with self.assertRaisesRegex(SyntaxError, r"unsafe node: Delete \(node not allowed\)"):
            safe_eval("del foo.bar", globals_dict={"foo": Foo()}, sandbox_instances=(Foo,), mode="exec")

    def test_11_deny_dunder_arg(self):
        with self.assertRaisesRegex(NameError, r"unsafe node: __test \(dunder name\)"):
            safe_eval("def f(x, *, __test): ...", mode="exec")

        with self.assertRaisesRegex(NameError, r"unsafe node: __test \(dunder name\)"):
            safe_eval("def f(x, /, __test): ...", mode="exec")

        with self.assertRaisesRegex(NameError, r"unsafe node: __test \(dunder name\)"):
            safe_eval("def f(x, *__test): ...", mode="exec")

    def test_12_deny_dangerous_func(self):
        with self.assertRaisesRegex(ValueError, r"unsafe object: <built-in function eval> \(denied by black-list\)"):
            safe_eval("eval('1')", mode="exec", globals_dict={"eval": eval})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <built-in function exec> \(denied by black-list\)"):
            safe_eval("exec('1')", mode="exec", globals_dict={"exec": exec})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <function safe_eval at *"):
            safe_eval("safe_eval('1')", mode="exec", globals_dict={"safe_eval": safe_eval})

        with self.assertRaisesRegex(ValueError, r"unsafe object: <built-in function system> \(denied by black-list\)"):
            safe_eval("system('echo')", mode="exec", globals_dict={"system": os.system})

        safe_eval("time.strftime('%Y-%m-%d')", mode="exec", globals_dict={"time": time})

    def test_13_deny_use_kwarg(self):
        with self.assertRaisesRegex(SyntaxError, "unsafe node: variadic keyword arguments"):
            safe_eval("def f(x, **kwargs): ...", mode="exec")

        with self.assertRaisesRegex(SyntaxError, "unsafe node: variadic keyword arguments"):
            safe_eval("lambda x, **kwargs: ...", mode="exec")

    def test_14_deny_use_decorator(self):
        with self.assertRaisesRegex(SyntaxError, "unsafe node: decorators"):
            safe_eval(cleandoc(
                """
                @foo
                def f(x):
                    ...
                """
            ), mode="exec")

    def test_15_deny_use_dunder_exception(self):
        with self.assertRaisesRegex(NameError, r"unsafe node: __type_checker \(dunder name\)"):
            safe_eval(cleandoc(
                """
                try:
                    ...
                except Exception as __type_checker:
                    ...
                """
            ), mode="exec")

    def test_16_globals_dict_leak_builtins(self):
        def set_locals(o):
            frame = o._SafeWrapper__obj.__traceback__.tb_frame
            frame.f_locals['is_injected'] = True
            frame.f_locals['__test__'] = 42

        globals_dict = {"__bad_stuff": 0, "set_locals": set_locals}
        locals_dict = {"__bad_stuff": 0}
        safe_eval(cleandoc(
            """
            try:
                1 / 0
            except Exception as e:
                set_locals(e)
            """
        ), globals_dict=globals_dict, locals_dict=locals_dict, mode="exec")
        self.assertNotIn("__builtins__", globals_dict)
        self.assertNotIn("__call_checker", globals_dict)
        self.assertNotIn("__type_checker", globals_dict)
        self.assertNotIn("__SafeWrapper", globals_dict)
        self.assertNotIn("__bad_stuff", globals_dict)
        self.assertNotIn("__bad_stuff", locals_dict)
        self.assertNotIn("__test__", locals_dict)
        self.assertTrue(locals_dict["is_injected"])

    @patch("odoo.tools.safe_eval.SafeWrapper.__getattr__")
    def test_17_bare_modules_becomes_wraps(self, mock):
        # If the `type_checker` detect a bare module, and that the module is in the white-list
        # then it should be wrapped in a SafeWrapper
        c = ast.unparse(CodeChecker(_AST_ALLOWED_NODES).visit(ast.parse("datetime.datetime")))
        glb = _prepare_environment()
        glb["__SafeWrapper"] = mock

        unsafe_eval(compile(c, "", "exec"), glb, {"datetime": datetime})
        mock.assert_called()

    def test_22_wrap_on_decorator(self):
        @allow_type
        class Foo:
            def __init__(self):
                ...

        def f(foo):
            return foo

        self.assertTrue(isinstance(safe_eval("f(Foo())", globals_dict={"f": f, "Foo": Foo}, mode="eval"), SafeWrapper))

    def test_18_deny_dunder_in_func(self):
        with self.assertRaisesRegex(NameError, r"unsafe node: __test \(dunder name\)"):
            safe_eval("def __test(): ...", mode="exec")

    def test_19_deny_async_func(self):
        with self.assertRaisesRegex(SyntaxError, r"unsafe node: AsyncFunctionDef \(node not allowed\)"):
            safe_eval("async def f(): ...", mode="exec")

    def test_20_cls_of_instances_are_denied(self):
        # The class "SafeWrapper" is not allowed to be used inside of the sandbox
        with self.assertRaisesRegex(ValueError, r"unsafe object: <class 'odoo.tools.safe_eval.SafeWrapper'>"):
            safe_eval("SafeWrapper(4)", mode="exec", globals_dict={"SafeWrapper": SafeWrapper})

        # But its instances are allowed
        safe_eval("a[0]", mode="exec", globals_dict={
            "a": SafeWrapper(__obj=[4], __type_checker=lambda **kwargs: kwargs["__obj"])})

    def test_21_globals_locals_work_properly(self):
        safe_eval(cleandoc("""
            def f():
                return sum(1,1)
            f()
        """), mode="exec", globals_dict={"sum": lambda x, y: x + y})

        safe_eval(cleandoc("""
            b = 4
            (lambda x: x + b)(4)
        """), mode="exec")

    def test_22_multiple_assign(self):
        safe_eval("a, b = 1, 2", mode="exec")
        safe_eval("t = (a, b) = (1, 2)", mode="exec")

        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval("a, b = get_sys()", mode="exec", globals_dict={"get_sys": lambda: [1, sys]})

        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval("*_, b = get_sys()", mode="exec", globals_dict={"get_sys": lambda: [1, 0, sys]})

        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval("*_, d['a'] = get_sys()", mode="exec", globals_dict={"get_sys": lambda: [1, 0, sys], "d": {}})

        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval(cleandoc("""
                for a, b in get_sys():
                    ...
            """), mode="exec", globals_dict={"get_sys": lambda: [[1, sys]]})

        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval(cleandoc("""
                for *_, b in get_sys():
                    ...
            """), mode="exec", globals_dict={"get_sys": lambda: [[1, 0, sys]]})

        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval(cleandoc("""
                [[a] for [[(a,), b, a]] in [[[*bim]]] ]
            """), mode="exec", globals_dict={"bim": ([sys], 2, sys)})

    def test_23_deny_use_of_bad_ref(self):
        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):
            safe_eval(cleandoc("""
                sys.argv
            """), mode="exec", globals_dict={"sys": sys})

    def test_24_bad_for_loop(self):
        with self.assertRaisesRegex(ValueError,
                                    r"unsafe object: <module 'sys' \(built-in\)> \(type not present in white-list\)"):

            safe_eval(cleandoc("""
                               for a in d:
                                   ...
            """), mode="exec", globals_dict={"d": sys})


class TestParentStore(TransactionCase):
    """ Verify that parent_store computation is done right """

    def setUp(self):
        super(TestParentStore, self).setUp()

        # force res_partner_category.copy() to copy children
        category = self.env['res.partner.category']
        self.patch(category._fields['child_ids'], 'copy', True)

        # setup categories
        self.root = category.create({'name': 'Root category'})
        self.cat0 = category.create({'name': 'Parent category', 'parent_id': self.root.id})
        self.cat1 = category.create({'name': 'Child 1', 'parent_id': self.cat0.id})
        self.cat2 = category.create({'name': 'Child 2', 'parent_id': self.cat0.id})
        self.cat21 = category.create({'name': 'Child 2-1', 'parent_id': self.cat2.id})

    def test_duplicate_parent(self):
        """ Duplicate the parent category and verify that the children have been duplicated too """
        new_cat0 = self.cat0.copy()
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_01(self):
        """ Duplicate the children then reassign them to the new parent (1st method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': []})
        (new_cat1 + new_cat2).write({'parent_id': new_cat0.id})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_02(self):
        """ Duplicate the children then reassign them to the new parent (2nd method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': [Command.set((new_cat1 + new_cat2).ids)]})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")

    def test_duplicate_children_03(self):
        """ Duplicate the children then reassign them to the new parent (3rd method). """
        new_cat1 = self.cat1.copy()
        new_cat2 = self.cat2.copy()
        new_cat0 = self.cat0.copy({'child_ids': []})
        new_cat0.write({'child_ids': [Command.link(new_cat1.id), Command.link(new_cat2.id)]})
        new_struct = new_cat0.search([('parent_id', 'child_of', new_cat0.id)])
        self.assertEqual(len(new_struct), 4, "After duplication, the new object must have the childs records")
        old_struct = new_cat0.search([('parent_id', 'child_of', self.cat0.id)])
        self.assertEqual(len(old_struct), 4, "After duplication, previous record must have old childs records only")
        self.assertFalse(new_struct & old_struct, "After duplication, nodes should not be mixed")


class TestGroups(TransactionCase):

    def test_res_groups_fullname_search(self):
        all_groups = self.env['res.groups'].search([])

        groups = all_groups.search([('full_name', 'like', 'Sale')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Sale' in g.full_name],
                              "did not match search for 'Sale'")

        groups = all_groups.search([('full_name', 'like', 'Technical')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Technical' in g.full_name],
                              "did not match search for 'Technical'")

        groups = all_groups.search([('full_name', 'like', 'Sales /')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Sales /' in g.full_name],
                              "did not match search for 'Sales /'")

        groups = all_groups.search([('full_name', 'in', ['Administration / Access Rights', 'Contact Creation'])])
        self.assertTrue(groups, "did not match search for 'Administration / Access Rights' and 'Contact Creation'")

    def test_res_group_has_cycle(self):
        # four groups with no cycle, check them all together
        a = self.env['res.groups'].create({'name': 'A'})
        b = self.env['res.groups'].create({'name': 'B'})
        c = self.env['res.groups'].create({'name': 'G', 'implied_ids': [Command.set((a + b).ids)]})
        d = self.env['res.groups'].create({'name': 'D', 'implied_ids': [Command.set(c.ids)]})
        self.assertFalse((a + b + c + d)._has_cycle('implied_ids'))

        # create a cycle and check
        a.implied_ids = d
        self.assertTrue(a._has_cycle('implied_ids'))

    def test_res_group_copy(self):
        a = self.env['res.groups'].with_context(lang='en_US').create({'name': 'A'})
        b = a.copy()
        self.assertNotEqual(a.name, b.name)

    def test_apply_groups(self):
        a = self.env['res.groups'].create({'name': 'A'})
        b = self.env['res.groups'].create({'name': 'B'})
        c = self.env['res.groups'].create({'name': 'C', 'implied_ids': [Command.set(a.ids)]})

        # C already implies A, we want both B+C to imply A
        (b + c)._apply_group(a)

        self.assertIn(a, b.implied_ids)
        self.assertIn(a, c.implied_ids)

    def test_remove_groups(self):
        u1 = self.env['res.users'].create({'login': 'u1', 'name': 'U1'})
        u2 = self.env['res.users'].create({'login': 'u2', 'name': 'U2'})
        default = self.env.ref('base.default_user')
        portal = self.env.ref('base.group_portal')
        p = self.env['res.users'].create({'login': 'p', 'name': 'P', 'groups_id': [Command.set([portal.id])]})

        a = self.env['res.groups'].create({'name': 'A', 'users': [Command.set(u1.ids)]})
        b = self.env['res.groups'].create({'name': 'B', 'users': [Command.set(u1.ids)]})
        c = self.env['res.groups'].create(
            {'name': 'C', 'implied_ids': [Command.set(a.ids)], 'users': [Command.set([p.id, u2.id, default.id])]})
        d = self.env['res.groups'].create(
            {'name': 'D', 'implied_ids': [Command.set(a.ids)], 'users': [Command.set([u2.id, default.id])]})

        def assertUsersEqual(users, group):
            self.assertEqual(
                sorted([r.login for r in users]),
                sorted([r.login for r in group.with_context(active_test=False).users])
            )

        # sanity checks
        assertUsersEqual([u1, u2, p, default], a)
        assertUsersEqual([u1], b)
        assertUsersEqual([u2, p, default], c)
        assertUsersEqual([u2, default], d)

        # C already implies A, we want none of B+C to imply A
        (b + c)._remove_group(a)

        self.assertNotIn(a, b.implied_ids)
        self.assertNotIn(a, c.implied_ids)
        self.assertIn(a, d.implied_ids)

        # - Since B didn't imply A, removing A from the implied groups of (B+C)
        #   should not remove user U1 from A, even though C implied A, since C does
        #   not have U1 as a user
        # - P should be removed as was only added via inheritance to C
        # - U2 should not be removed from A since it is implied via C but also via D
        assertUsersEqual([u1, u2, default], a)
        assertUsersEqual([u1], b)
        assertUsersEqual([u2, p, default], c)
        assertUsersEqual([u2, default], d)

        # When adding the template user to a new group, it should add it to existing internal users
        e = self.env['res.groups'].create({'name': 'E'})
        default.write({'groups_id': [Command.link(e.id)]})
        self.assertIn(u1, e.users)
        self.assertIn(u2, e.users)
        self.assertIn(default, e.with_context(active_test=False).users)
        self.assertNotIn(p, e.users)
