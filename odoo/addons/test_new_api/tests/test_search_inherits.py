# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo import Command


class TestSearchInherits(TransactionCase):

    def patch_order(self, model, order):
        self.patch(self.registry[model], '_order', order)

    def test_10_inherits_m2order(self):
        Users = self.env['res.users.inherits']

        # Find Employee group
        group_employee = self.env.ref('base.group_user')

        # Get country/state data
        country_be = self.env.ref('base.be')
        country_us = self.env.ref('base.us')
        states_us = country_us.state_ids[:2]

        # Create test users
        user = self.env['res.users'].create({'name': '__search', 'login': '__search', 'groups_id': [Command.set([group_employee.id])]})

        u = Users.create({'name': '__search', 'login': '__search'})
        a = Users.create({'name': '__test_A', 'login': '__test_A', 'country_id': country_be.id, 'state_id': country_be.id})
        b = Users.create({'name': '__test_B', 'login': '__a_test_B', 'country_id': country_us.id, 'state_id': states_us[1].id})
        c = Users.create({'name': '__test_B', 'login': '__z_test_B', 'country_id': country_us.id, 'state_id': states_us[0].id})

        # Search as search user
        Users = Users.with_user(user)

        # Do: search on res.users.inherits, order on a field on res.partner.inherits to try inherits'd fields, then res.users.inherits
        expected_ids = [u.id, a.id, c.id, b.id]
        user_ids = Users.search([('id', 'in', expected_ids)], order='name asc, login desc').ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one and inherits'd fields
        expected_ids = [c.id, b.id, a.id, u.id]
        user_ids = Users.search([('id', 'in', expected_ids)], order='state_id asc, country_id desc, name asc, login desc').ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one and inherits'd fields
        expected_ids = [u.id, b.id, c.id, a.id]
        user_ids = Users.search([('id', 'in', expected_ids)], order='country_id desc, state_id desc, name asc, login desc').ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one, but not by specifying in order parameter of search, but by overriding _order of res_users
        self.patch_order('res.users.inherits', 'country_id desc, name asc, login desc')
        expected_ids = [u.id, c.id, b.id, a.id]
        user_ids = Users.search([('id', 'in', expected_ids)]).ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')
