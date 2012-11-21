import unittest2

import openerp.tests.common as common

class test_expression(common.TransactionCase):

    def test_search_order(self):

        registry, cr, uid = self.registry, self.cr, self.uid

        # Create 6 partners with a given name, and a given creation order to ensure the order of their ID. Some are set as unactive to verify they are by default excluded from the searchs and to provide a second order argument

        partners = registry('res.partner')
        c = partners.create(cr, uid, {'name': 'test_search_order_C'})
        d = partners.create(cr, uid, {'name': 'test_search_order_D', 'active': False})
        a = partners.create(cr, uid, {'name': 'test_search_order_A'})
        b = partners.create(cr, uid, {'name': 'test_search_order_B'})
        ab = partners.create(cr, uid, {'name': 'test_search_order_AB'})
        e = partners.create(cr, uid, {'name': 'test_search_order_E', 'active': False})

        # The tests.

        # The basic searchs should exclude records that have active = False. The order of ids returned 
        # should be given by the 'order' parameter of search()

        name_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="name asc")
        self.assertEqual([a, ab, b, c], name_asc, "Search with 'NAME ASC' order failed.")
        name_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="name desc")
        self.assertEqual([c, b, ab, a], name_desc, "Search with 'NAME DESC' order failed.")
        id_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="id asc")
        self.assertEqual([c, a, b, ab], id_asc, "Search with 'ID ASC' order failed.")
        id_desc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="id desc")
        self.assertEqual([ab, b, a, c], id_desc, "Search with 'ID DESC' order failed.")

        # The inactive records shouldn't be ecxluded as soon as a condition on this field is present in the domain 
        # criteria. The 'order' parameter of search() should support any valable coma-separated value

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


