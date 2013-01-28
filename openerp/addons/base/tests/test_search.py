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
        old_order = users_obj._order
        users_obj._order = 'country_id desc, name asc, login desc'
        user_ids = users_obj.search(cr, search_user, [])
        expected_ids = [search_user, c, b, a]
        test_user_ids = filter(lambda x: x in expected_ids, user_ids)
        self.assertEqual(test_user_ids, expected_ids, 'search on res_users did not provide expected ids or expected order')
        users_obj._order = old_order


if __name__ == '__main__':
    unittest2.main()
