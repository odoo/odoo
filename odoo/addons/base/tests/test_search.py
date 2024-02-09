# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo import Command


class test_search(TransactionCase):

    def patch_order(self, model, order):
        self.patch(self.registry[model], '_order', order)

    def test_00_search_order(self):
        # Create 6 partners with a given name, and a given creation order to
        # ensure the order of their ID. Some are set as inactive to verify they
        # are by default excluded from the searches and to provide a second
        # `order` argument.

        Partner = self.env['res.partner']
        c = Partner.create({'name': 'test_search_order_C'})
        d = Partner.create({'name': 'test_search_order_D', 'active': False})
        a = Partner.create({'name': 'test_search_order_A'})
        b = Partner.create({'name': 'test_search_order_B'})
        ab = Partner.create({'name': 'test_search_order_AB'})
        e = Partner.create({'name': 'test_search_order_E', 'active': False})

        # The tests.

        # The basic searches should exclude records that have active = False.
        # The order of the returned ids should be given by the `order`
        # parameter of search().

        name_asc = Partner.search([('name', 'like', 'test_search_order%')], order="name asc")
        self.assertEqual([a, ab, b, c], list(name_asc), "Search with 'NAME ASC' order failed.")
        name_desc = Partner.search([('name', 'like', 'test_search_order%')], order="name desc")
        self.assertEqual([c, b, ab, a], list(name_desc), "Search with 'NAME DESC' order failed.")
        id_asc = Partner.search([('name', 'like', 'test_search_order%')], order="id asc")
        self.assertEqual([c, a, b, ab], list(id_asc), "Search with 'ID ASC' order failed.")
        id_desc = Partner.search([('name', 'like', 'test_search_order%')], order="id desc")
        self.assertEqual([ab, b, a, c], list(id_desc), "Search with 'ID DESC' order failed.")

        # The inactive records shouldn't be excluded as soon as a condition on
        # that field is present in the domain. The `order` parameter of
        # search() should support any legal coma-separated values.

        active_asc_id_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active asc, id asc")
        self.assertEqual([d, e, c, a, b, ab], list(active_asc_id_asc), "Search with 'ACTIVE ASC, ID ASC' order failed.")
        active_desc_id_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active desc, id asc")
        self.assertEqual([c, a, b, ab, d, e], list(active_desc_id_asc), "Search with 'ACTIVE DESC, ID ASC' order failed.")
        active_asc_id_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active asc, id desc")
        self.assertEqual([e, d, ab, b, a, c], list(active_asc_id_desc), "Search with 'ACTIVE ASC, ID DESC' order failed.")
        active_desc_id_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active desc, id desc")
        self.assertEqual([ab, b, a, c, e, d], list(active_desc_id_desc), "Search with 'ACTIVE DESC, ID DESC' order failed.")
        id_asc_active_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id asc, active asc")
        self.assertEqual([c, d, a, b, ab, e], list(id_asc_active_asc), "Search with 'ID ASC, ACTIVE ASC' order failed.")
        id_asc_active_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id asc, active desc")
        self.assertEqual([c, d, a, b, ab, e], list(id_asc_active_desc), "Search with 'ID ASC, ACTIVE DESC' order failed.")
        id_desc_active_asc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id desc, active asc")
        self.assertEqual([e, ab, b, a, d, c], list(id_desc_active_asc), "Search with 'ID DESC, ACTIVE ASC' order failed.")
        id_desc_active_desc = Partner.search([('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id desc, active desc")
        self.assertEqual([e, ab, b, a, d, c], list(id_desc_active_desc), "Search with 'ID DESC, ACTIVE DESC' order failed.")

        a.ref = "ref1"
        c.ref = "ref2"
        ids = (a | b | c).ids
        for order, result in [
            ('ref', a | c | b),
            ('ref desc', b | c | a),
            ('ref asc nulls first', b | a | c),
            ('ref asc nulls last', a | c | b),
            ('ref desc nulls first', b | c | a),
            ('ref desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # sorting by an m2o should alias to the natural order of the m2o
        self.patch_order('res.country', 'phone_code')
        a.country_id, c.country_id = self.env['res.country'].create([{
            'name': "Country 1",
            'code': 'C1',
            'phone_code': '01',
        }, {
            'name': 'Country 2',
            'code': 'C2',
            'phone_code': '02'
        }])

        for order, result in [
            ('country_id', a | c | b),
            ('country_id desc', b | c | a),
            ('country_id asc nulls first', b | a | c),
            ('country_id asc nulls last', a | c | b),
            ('country_id desc nulls first', b | c | a),
            ('country_id desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # NULLS applies to the m2o itself, not its sub-fields, so a null `phone_code`
        # will sort normally (larger than non-null codes)
        b.country_id = self.env['res.country'].create({'name': "Country X", 'code': 'C3'})

        for order, result in [
            ('country_id', a | c | b),
            ('country_id desc', b | c | a),
            ('country_id asc nulls first', a | c | b),
            ('country_id asc nulls last', a | c | b),
            ('country_id desc nulls first', b | c | a),
            ('country_id desc nulls last', b | c | a)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # a field DESC should reverse the nested behaviour (and thus the inner
        # NULLS clauses), but the outer NULLS clause still has no effect
        self.patch_order('res.country', 'phone_code NULLS FIRST')
        for order, result in [
            ('country_id', b | a | c),
            ('country_id desc', c | a | b),
            ('country_id asc nulls first', b | a | c),
            ('country_id asc nulls last', b | a | c),
            ('country_id desc nulls first', c | a | b),
            ('country_id desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

    def test_10_inherits_m2order(self):
        Users = self.env['res.users']

        # Find Employee group
        group_employee = self.env.ref('base.group_user')

        # Get country/state data
        country_be = self.env.ref('base.be')
        country_us = self.env.ref('base.us')
        states_us = country_us.state_ids[:2]

        # Create test users
        u = Users.create({'name': '__search', 'login': '__search', 'groups_id': [Command.set([group_employee.id])]})
        a = Users.create({'name': '__test_A', 'login': '__test_A', 'country_id': country_be.id, 'state_id': country_be.id})
        b = Users.create({'name': '__test_B', 'login': '__a_test_B', 'country_id': country_us.id, 'state_id': states_us[1].id})
        c = Users.create({'name': '__test_B', 'login': '__z_test_B', 'country_id': country_us.id, 'state_id': states_us[0].id})

        # Search as search user
        Users = Users.with_user(u)

        # Do: search on res.users, order on a field on res.partner to try inherits'd fields, then res.users
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
        self.patch_order('res.users', 'country_id desc, name asc, login desc')
        expected_ids = [u.id, c.id, b.id, a.id]
        user_ids = Users.search([('id', 'in', expected_ids)]).ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

    def test_11_indirect_inherits_m2o_order(self):
        Cron = self.env['ir.cron']
        Users = self.env['res.users']

        user_ids = {}
        cron_ids = {}
        for u in 'BAC':
            user_ids[u] = Users.create({'name': u, 'login': u}).id
            cron_ids[u] = Cron.create({'name': u, 'model_id': self.env.ref('base.model_res_partner').id, 'user_id': user_ids[u]}).id

        ids = Cron.search([('id', 'in', list(cron_ids.values()))], order='user_id').ids
        expected_ids = [cron_ids[l] for l in 'ABC']
        self.assertEqual(ids, expected_ids)

    def test_12_m2o_order_loop_self(self):
        Cats = self.env['ir.module.category']
        cat_ids = {}
        def create(name, **kw):
            cat_ids[name] = Cats.create(dict(kw, name=name)).id

        self.patch_order('ir.module.category', 'parent_id desc, name')

        create('A')
        create('B', parent_id=cat_ids['A'])
        create('C', parent_id=cat_ids['A'])
        create('D')
        create('E', parent_id=cat_ids['D'])
        create('F', parent_id=cat_ids['D'])

        expected_ids = [cat_ids[x] for x in 'ADEFBC']
        found_ids = Cats.search([('id', 'in', list(cat_ids.values()))]).ids
        self.assertEqual(found_ids, expected_ids)

    def test_13_m2o_order_loop_multi(self):
        Users = self.env['res.users']

        # will sort by login desc of the creator, then by name
        self.patch_order('res.partner', 'create_uid, name')
        self.patch_order('res.users', 'partner_id, login desc')

        kw = dict(groups_id=[Command.set([self.ref('base.group_system'),
                                     self.ref('base.group_partner_manager')])])

        u1 = Users.create(dict(name='Q', login='m', **kw)).id
        u2 = Users.with_user(u1).create(dict(name='B', login='f', **kw)).id
        u3 = Users.create(dict(name='C', login='c', **kw)).id
        u4 = Users.with_user(u2).create(dict(name='D', login='z', **kw)).id

        expected_ids = [u2, u4, u3, u1]
        found_ids = Users.search([('id', 'in', expected_ids)]).ids
        self.assertEqual(found_ids, expected_ids)

    def test_20_x_active(self):
        """Check the behaviour of the x_active field."""
        # test that a custom field x_active filters like active
        # we take the model res.country as a test model as it is included in base and does
        # not have an active field
        model_country = self.env['res.country']
        self.assertNotIn('active', model_country._fields)  # just in case someone adds the active field in the model
        self.env['ir.model.fields'].create({
            'name': 'x_active',
            'model_id': self.env.ref('base.model_res_country').id,
            'ttype': 'boolean',
        })
        self.assertEqual('x_active', model_country._active_name)
        country_ussr = model_country.create({'name': 'USSR', 'x_active': False, 'code': 'ZV'})
        ussr_search = model_country.search([('name', '=', 'USSR')])
        self.assertFalse(ussr_search)
        ussr_search = model_country.with_context(active_test=False).search([('name', '=', 'USSR')])
        self.assertIn(country_ussr, ussr_search, "Search with active_test on a custom x_active field failed")
        ussr_search = model_country.search([('name', '=', 'USSR'), ('x_active', '=', False)])
        self.assertIn(country_ussr, ussr_search, "Search with active_test on a custom x_active field failed")
        # test that a custom field x_active on a model with the standard active
        # field does not interfere with the standard behaviour
        # use res.bank since it has an active field and is simple to use
        model_bank = self.env['res.bank']
        self.env['ir.model.fields'].create({
            'name': 'x_active',
            'model_id': self.env.ref('base.model_res_bank').id,
            'ttype': 'boolean',
        })
        self.assertEqual('active', model_bank._active_name)
        bank_credit_communal = model_bank.create({'name': 'Crédit Communal', 'x_active': False, 'active': True})
        cc_search = model_bank.search([('name', '=', 'Crédit Communal')])
        self.assertIn(bank_credit_communal, cc_search, "Search for active record with x_active set to False has failed")
        bank_credit_communal.write({
            'active': False,
            'x_active': True,
        })
        cc_search = model_bank.search([('name', '=', 'Crédit Communal')])
        self.assertNotIn(bank_credit_communal, cc_search, "Search for inactive record with x_active set to True has failed")

    def test_21_search_count(self):
        Partner = self.env['res.partner']
        count_partner_before = Partner.search_count([])
        partners = Partner.create([
            {'name': 'abc'},
            {'name': 'zer'},
            {'name': 'christope'},
            {'name': 'runbot'},
        ])
        self.assertEqual(len(partners) + count_partner_before, Partner.search_count([]))
        self.assertEqual(3, Partner.search_count([], limit=3))

    def test_22_large_domain(self):
        """ Ensure search and its unerlying SQL mechanism is able to handle large domains"""
        N = 9500
        domain = ['|'] * (N - 1) + [('login', '=', 'admin')] * N
        self.env['res.users'].search(domain)
