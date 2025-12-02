# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from textwrap import dedent

from odoo import Command
from odoo.tests.common import TransactionCase, BaseCase
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval, const_eval, expr_eval


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
        monkey = self.env['res.groups.privilege'].create({'name': 'Monkey'})
        self.env['res.groups']._load_records([{
            'xml_id': 'base.test_monkey_banana',
            'values': {'name': 'Banana', 'privilege_id': monkey.id},
        }, {
            'xml_id': 'base.test_monkey_stuff',
            'values': {'name': 'Stuff', 'privilege_id': monkey.id},
        }, {
            'xml_id': 'base.test_monkey_administrator',
            'values': {'name': 'Administrator', 'privilege_id': monkey.id},
        }, {
            'xml_id': 'base.test_donky',
            'values': {'name': 'Donky Monkey'},
        }])

        all_groups = self.env['res.groups'].search([])

        groups = all_groups.search([('full_name', 'like', 'Sale')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Sale' in g.full_name],
                              "did not match search for 'Sale'")

        groups = all_groups.search([('full_name', 'like', 'Master Data')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Master Data' in g.full_name],
                              "did not match search for 'Master Data'")

        groups = all_groups.search([('full_name', 'like', 'Monkey/Banana')])
        self.assertItemsEqual(groups.mapped('full_name'), ['Monkey / Banana'],
                              "did not match search for 'Monkey/Banana'")

        groups = all_groups.search([('full_name', 'like', 'Monkey /')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Monkey /' in g.full_name],
                              "did not match search for 'Monkey /'")

        groups = all_groups.search([('full_name', 'like', 'Monk /')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Monkey /' in g.full_name],
                              "did not match search for 'Monk /'")

        groups = all_groups.search([('full_name', 'like', 'Monk')])
        self.assertItemsEqual(groups.ids, [g.id for g in all_groups if 'Monk' in g.full_name],
                              "did not match search for 'Monk'")

        groups = all_groups.search([('full_name', 'in', ['Creation'])])
        self.assertItemsEqual(groups.mapped('full_name'), ['Contact / Creation'])

        groups = all_groups.search([('full_name', 'in', ['Role / Administrator', 'Creation'])])
        self.assertItemsEqual(groups.mapped('full_name'), ['Contact / Creation', 'Role / Administrator'])

        groups = all_groups.search([('full_name', 'like', 'Admin')])
        self.assertItemsEqual(groups.mapped('full_name'), [g.full_name for g in all_groups if 'Admin' in g.full_name])

        groups = all_groups.search([('full_name', 'not like', 'Role /')])
        self.assertItemsEqual(groups.mapped('full_name'), [g.full_name for g in all_groups if 'Role /' not in g.full_name])

        groups = all_groups.search([('full_name', '=', False)])
        self.assertFalse(groups)

        groups = all_groups.search([('full_name', '!=', False)])
        self.assertEqual(groups, all_groups)

        groups = all_groups.search([('full_name', 'like', '/')])
        self.assertTrue(groups, "did not match search for '/'")

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
        portal = self.env.ref('base.group_portal')
        p = self.env['res.users'].create({'login': 'p', 'name': 'P', 'group_ids': [Command.set([portal.id])]})

        a = self.env['res.groups'].create({'name': 'A', 'user_ids': [Command.set(u1.ids)]})
        b = self.env['res.groups'].create({'name': 'B', 'user_ids': [Command.set(u1.ids)]})
        c = self.env['res.groups'].create({'name': 'C', 'implied_ids': [Command.set(a.ids)], 'user_ids': [Command.set([p.id, u2.id])]})
        d = self.env['res.groups'].create({'name': 'D', 'implied_ids': [Command.set(a.ids)], 'user_ids': [Command.set([u2.id])]})

        def assertUsersEqual(users, group):
            self.assertEqual(
                sorted([r.login for r in users]),
                sorted(group.with_context(active_test=False).mapped('all_user_ids.login'))
            )
        # sanity checks
        assertUsersEqual([u1, u2, p], a)
        assertUsersEqual([u1], b)
        assertUsersEqual([u2, p], c)
        assertUsersEqual([u2], d)

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
        assertUsersEqual([u1, u2], a)
        assertUsersEqual([u1], b)
        assertUsersEqual([u2, p], c)
        assertUsersEqual([u2], d)

        # When adding a new group to all users
        e = self.env['res.groups'].create({'name': 'E'})
        self.env.ref('base.group_user').write({'implied_ids': [Command.link(e.id)]})
        self.assertIn(u1, e.all_user_ids)
        self.assertIn(u2, e.all_user_ids)
        self.assertNotIn(p, e.all_user_ids)
