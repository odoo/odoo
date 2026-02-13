# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, TransactionCase, Form


@tagged('at_install', '-post_install')  # LEGACY at_install
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


class TestResGroupForm(TransactionCase):
    def test_create_res_group(self):
        group_form = Form(self.env['res.groups'])
        group_form.name = 'a group'
        group_form.save()
