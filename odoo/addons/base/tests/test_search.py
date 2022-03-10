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
        country_ussr = model_country.create({'name': 'USSR', 'x_active': False})
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
