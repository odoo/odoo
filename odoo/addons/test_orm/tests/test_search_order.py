# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSearch(TransactionCase):

    def patch_order(self, model, order):
        self.patch(self.registry[model], '_order', order)

    def test_00_search_order(self):
        # Create 6 partners with a given name, and a given creation order to
        # ensure the order of their ID. Some are set as inactive to verify they
        # are by default excluded from the searches and to provide a second
        # `order` argument.

        Partner = self.env['test_orm.partner']
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

        a.email = "email1"
        c.email = "email2"
        ids = (a | b | c).ids
        for order, result in [
            ('email', a | c | b),
            ('email desc', b | c | a),
            ('email asc nulls first', b | a | c),
            ('email asc nulls last', a | c | b),
            ('email desc nulls first', b | c | a),
            ('email desc nulls last', c | a | b)
        ]:
            with self.subTest(order):
                self.assertEqual(
                    Partner.search([('id', 'in', ids)], order=order).mapped('name'),
                    result.mapped('name'))

        # sorting by an m2o should alias to the natural order of the m2o
        self.patch_order('test_orm.country', 'phone_code')
        a.country_id, c.country_id = self.env['test_orm.country'].create([{
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
        b.country_id = self.env['test_orm.country'].create({'name': "Country X", 'code': 'C3'})

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
        self.patch_order('test_orm.country', 'phone_code NULLS FIRST')
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
        Users = self.env['test_orm.search.order.users']

        country_be = self.env['test_orm.country'].create({'name': 'Belgium'})
        country_us = self.env['test_orm.country'].create({'name': 'United States'})
        states_us = self.env['test_orm.country.state'].create([
            {'name': 'Armed Forces Americas', 'country_id': country_us.id},
            {'name': 'Armed Forces Europe', 'country_id': country_us.id},
        ])
        states_be = self.env['test_orm.country.state'].create({'name': 'Antwerpen', 'country_id': country_be.id})

        # Create test users
        u = Users.create({'name': '__search', 'login': '__search'})
        a = Users.create({'name': '__test_A', 'login': '__test_A', 'country_id': country_be.id, 'state_id': states_be[0].id})  # Antwerpen
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
        self.patch_order('test_orm.search.order.users', 'country_id desc, name asc, login desc')
        expected_ids = [u.id, c.id, b.id, a.id]
        user_ids = Users.search([('id', 'in', expected_ids)]).ids
        self.assertEqual(user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

    def test_11_indirect_inherits_m2o_order(self):
        self.patch_order('test_orm.search.order.alpha', 'id')
        self.patch_order('test_orm.search.order.beta', 'name')

        model_ids = {}

        for name in 'BAC':
            model_ids[name] = self.env['test_orm.search.order.alpha'].create({
                'name': name,
                'beta_id': self.env['test_orm.search.order.beta'].create({'name': name}).id
            }).id

        found_ids = self.env['test_orm.search.order.alpha'].search([('id', 'in', list(model_ids.values()))], order='beta_id').ids
        expected_ids = [model_ids[name] for name in 'ABC']

        self.assertEqual(found_ids, expected_ids)

    def test_12_m2o_order_loop_self(self):
        Model = self.env['test_orm.search.order.alpha']
        model_ids = {}

        self.patch_order('test_orm.search.order.alpha', 'alpha_loop_id desc, name')

        model_ids['A'] = Model.create({'name': 'A'}).id
        model_ids['B'] = Model.create({'name': 'B', 'alpha_loop_id': model_ids['A']}).id
        model_ids['C'] = Model.create({'name': 'C', 'alpha_loop_id': model_ids['A']}).id
        model_ids['D'] = Model.create({'name': 'D'}).id
        model_ids['E'] = Model.create({'name': 'E', 'alpha_loop_id': model_ids['D']}).id
        model_ids['F'] = Model.create({'name': 'F', 'alpha_loop_id': model_ids['D']}).id

        found_ids = Model.search([('id', 'in', list(model_ids.values()))]).ids
        expected_ids = [model_ids[name] for name in 'ADEFBC']

        self.assertEqual(found_ids, expected_ids)

    def test_13_m2o_order_loop_multi(self):
        Model = self.env['test_orm.search.order.users']

        # will sort by login desc of the creator, then by name
        self.patch_order('test_orm.search.order.partner', 'user_id, name')
        self.patch_order('test_orm.search.order.users', 'partner_id, login desc')

        u0 = Model.create(dict(name='A system', login='a')).id

        u1 = Model.create(dict(name='Q', login='m', user_id=u0)).id
        u2 = Model.create(dict(name='B', login='f', user_id=u1)).id
        u3 = Model.create(dict(name='C', login='c', user_id=u0)).id
        u4 = Model.create(dict(name='D', login='z', user_id=u2)).id

        expected_ids = [u2, u4, u3, u1]
        found_ids = Model.search([('id', 'in', expected_ids)]).ids

        self.assertEqual(found_ids, expected_ids)

    def test_20_x_active(self):
        """Check the behaviour of the x_active field."""
        # test that a custom field x_active filters like active
        # we take the model res.country as a test model as it is included in base and does
        # not have an active field
        self.addCleanup(self.registry.reset_changes) # reset the registry to avoid polluting other tests

        model_country = self.env['test_orm.country']
        self.assertNotIn('active', model_country._fields)  # just in case someone adds the active field in the model
        self.env['ir.model.fields'].create({
            'name': 'x_active',
            'model_id': self.env.ref('test_orm.model_test_orm_country').id,
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

    def test_21_search_count(self):
        Partner = self.env['test_orm.partner']
        count_partner_before = Partner.search_count([])
        partners = Partner.create([
            {'name': 'abc'},
            {'name': 'zer'},
            {'name': 'christope'},
            {'name': 'runbot'},
        ])
        self.assertEqual(len(partners) + count_partner_before, Partner.search_count([]))
        self.assertEqual(3, Partner.search_count([], limit=3))

    def test_22_like_folding(self):
        Model = self.env['test_orm.country']

        self.patch_order('test_orm.country', 'name, id')

        # there is just one query for the first search as it matches all
        # the second search does not run, because the domain is False
        with self.assertQueries(["""
            SELECT "test_orm_country"."id"
            FROM "test_orm_country"
            ORDER BY "test_orm_country"."name", "test_orm_country"."id"
        """]):
            Model.search([('code', 'ilike', '')])
            Model.search([('code', 'not ilike', '')])
