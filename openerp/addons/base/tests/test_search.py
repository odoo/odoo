import unittest2

import openerp.tests.common as common


class test_search(common.TransactionCase):

    def test_00_search_order(self):

        registry, cr, uid = self.registry, self.cr, self.uid

        # Create 6 partners with a given name, and a given creation order to
        # ensure the order of their ID. Some are set as unactive to verify they
        # are by default excluded from the searches and to provide a second
        # `order` argument.

        partners = registry('res.partner')
        c = partners.create(cr, uid, {'name': 'test_search_order_C'})
        d = partners.create(cr, uid, {'name': 'test_search_order_D', 'active': False})
        a = partners.create(cr, uid, {'name': 'test_search_order_A'})
        b = partners.create(cr, uid, {'name': 'test_search_order_B'})
        ab = partners.create(cr, uid, {'name': 'test_search_order_AB'})
        e = partners.create(cr, uid, {'name': 'test_search_order_E', 'active': False})

        # The tests.

        # The basic searches should exclude records that have active = False.
        # The order of the returned ids should be given by the `order`
        # parameter of search().

        name_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="name asc")
        self.assertEqual([a, ab, b, c], name_asc, "Search with 'NAME ASC' order failed.")
        name_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="name desc")
        self.assertEqual([c, b, ab, a], name_desc, "Search with 'NAME DESC' order failed.")
        id_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="id asc")
        self.assertEqual([c, a, b, ab], id_asc, "Search with 'ID ASC' order failed.")
        id_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="id desc")
        self.assertEqual([ab, b, a, c], id_desc, "Search with 'ID DESC' order failed.")

        # The inactive records shouldn't be excluded as soon as a condition on
        # that field is present in the domain. The `order` parameter of
        # search() should support any legal coma-separated values.

        active_asc_id_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active asc, id asc")
        self.assertEqual([d, e, c, a, b, ab], active_asc_id_asc, "Search with 'ACTIVE ASC, ID ASC' order failed.")
        active_desc_id_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active desc, id asc")
        self.assertEqual([c, a, b, ab, d, e], active_desc_id_asc, "Search with 'ACTIVE DESC, ID ASC' order failed.")
        active_asc_id_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active asc, id desc")
        self.assertEqual([e, d, ab, b, a, c], active_asc_id_desc, "Search with 'ACTIVE ASC, ID DESC' order failed.")
        active_desc_id_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="active desc, id desc")
        self.assertEqual([ab, b, a, c, e, d], active_desc_id_desc, "Search with 'ACTIVE DESC, ID DESC' order failed.")
        id_asc_active_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id asc, active asc")
        self.assertEqual([c, d, a, b, ab, e], id_asc_active_asc, "Search with 'ID ASC, ACTIVE ASC' order failed.")
        id_asc_active_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id asc, active desc")
        self.assertEqual([c, d, a, b, ab, e], id_asc_active_desc, "Search with 'ID ASC, ACTIVE DESC' order failed.")
        id_desc_active_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id desc, active asc")
        self.assertEqual([e, ab, b, a, d, c], id_desc_active_asc, "Search with 'ID DESC, ACTIVE ASC' order failed.")
        id_desc_active_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%'), '|', ('active', '=', True), ('active', '=', False)], order="id desc, active desc")
        self.assertEqual([e, ab, b, a, d, c], id_desc_active_desc, "Search with 'ID DESC, ACTIVE DESC' order failed.")

    def test_10_inherits_m2order(self):
        registry, cr, uid = self.registry, self.cr, self.uid
        users_obj = registry('res.users')

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Get country/state data
        country_us_id = registry('res.country').search(cr, uid, [('code', 'like', 'US')])[0]
        state_ids = registry('res.country.state').search(cr, uid, [('country_id', '=', country_us_id)], limit=2)
        country_be_id = registry('res.country').search(cr, uid, [('code', 'like', 'BE')])[0]

        # Create test users
        search_user = users_obj.create(cr, uid, {'name': '__search', 'login': '__search', 'groups_id': [(6, 0, [group_employee_id])]})
        a = users_obj.create(cr, uid, {'name': '__test_A', 'login': '__test_A', 'country_id': country_be_id, 'state_id': country_be_id})
        b = users_obj.create(cr, uid, {'name': '__test_B', 'login': '__a_test_B', 'country_id': country_us_id, 'state_id': state_ids[1]})
        c = users_obj.create(cr, uid, {'name': '__test_B', 'login': '__z_test_B', 'country_id': country_us_id, 'state_id': state_ids[0]})

        # Do: search on res.users, order on a field on res.partner to try inherits'd fields, then res.users
        user_ids = users_obj.search(cr, search_user, [], order='name asc, login desc')
        expected_ids = [search_user, a, c, b]
        test_user_ids = filter(lambda x: x in expected_ids, user_ids)
        self.assertEqual(test_user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one and inherits'd fields
        user_ids = users_obj.search(cr, search_user, [], order='state_id asc, country_id desc, name asc, login desc')
        expected_ids = [c, b, a, search_user]
        test_user_ids = filter(lambda x: x in expected_ids, user_ids)
        self.assertEqual(test_user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one and inherits'd fields
        user_ids = users_obj.search(cr, search_user, [], order='country_id desc, state_id desc, name asc, login desc')
        expected_ids = [search_user, b, c, a]
        test_user_ids = filter(lambda x: x in expected_ids, user_ids)
        self.assertEqual(test_user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

        # Do: order on many2one, but not by specifying in order parameter of search, but by overriding _order of res_users
        self.patch_order('res.users', 'country_id desc, name asc, login desc')
        user_ids = users_obj.search(cr, search_user, [])
        expected_ids = [search_user, c, b, a]
        test_user_ids = filter(lambda x: x in expected_ids, user_ids)
        self.assertEqual(test_user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')

    def test_11_indirect_inherits_m2o_order(self):
        registry, cr, uid = self.registry, self.cr, self.uid
        Cron = registry('ir.cron')
        Users = registry('res.users')

        user_ids = {}
        cron_ids = {}
        for u in 'BAC':
            user_ids[u] = Users.create(cr, uid, {'name': u, 'login': u})
            cron_ids[u] = Cron.create(cr, uid, {'name': u, 'user_id': user_ids[u]})

        ids = Cron.search(cr, uid, [('id', 'in', cron_ids.values())], order='user_id')
        expected_ids = [cron_ids[l] for l in 'ABC']
        self.assertEqual(ids, expected_ids)

    def test_12_m2o_order_loop_self(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        Cats = registry('ir.module.category')
        ids = {}
        def create(name, **kw):
            ids[name] = Cats.create(cr, uid, dict(kw, name=name))

        self.patch_order('ir.module.category', 'parent_id desc, name')

        create('A')
        create('B', parent_id=ids['A'])
        create('C', parent_id=ids['A'])
        create('D')
        create('E', parent_id=ids['D'])
        create('F', parent_id=ids['D'])

        expected_order = [ids[x] for x in 'ADEFBC']
        domain = [('id', 'in', ids.values())]
        search_result = Cats.search(cr, uid, domain)
        self.assertEqual(search_result, expected_order)

    def test_13_m2o_order_loop_multi(self):
        Users = self.env['res.users']

        # will sort by login desc of the creator, then by name
        self.patch_order('res.partner', 'create_uid, name')
        self.patch_order('res.users', 'partner_id, login desc')

        kw = dict(groups_id=[(6, 0, [self.ref('base.group_system'),
                                     self.ref('base.group_partner_manager')])])

        u1 = Users.create(dict(name='Q', login='m', **kw)).id
        u2 = Users.sudo(user=u1).create(dict(name='B', login='f', **kw)).id
        u3 = Users.create(dict(name='C', login='c', **kw)).id
        u4 = Users.sudo(user=u2).create(dict(name='D', login='z', **kw)).id

        expected_order = [u2, u4, u3, u1]

        domain = [('id', 'in', [u1, u2, u3, u4])]
        search_result = list(Users.search(domain)._ids)
        self.assertEqual(search_result, expected_order)

if __name__ == '__main__':
    unittest2.main()
