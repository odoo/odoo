# -*- coding: utf-8 -*-

from odoo.tests import common


class TestStockLocationSearch(common.TransactionCase):
    def setUp(self):
        super(TestStockLocationSearch, self).setUp()
        user_group_stock_user = self.env.ref('stock.group_stock_user')
        user_group_stock_manager = self.env.ref('stock.group_stock_manager')

        Users = self.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        self.user_stock_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_stock_user.id])]})
        self.user_stock_manager = Users.create({
            'name': 'Julie Tablier',
            'login': 'julie',
            'email': 'j.j@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_stock_manager.id])]})

        self.location = self.env['stock.location']
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.sublocation = self.env['stock.location'].create({
            'name': 'Shelf 2',
            'barcode': 1201985,
            'location_id': self.stock_location.id
        })
        self.location_barcode_id = self.sublocation.id
        self.barcode = self.sublocation.barcode
        self.name = self.sublocation.name
        self.env = self.env(user=self.user_stock_user)

    def test_10_location_search_by_barcode(self):
        """Search stock location by barcode"""
        location_names = self.location.name_search(name=self.barcode)
        self.assertEqual(len(location_names), 1)
        location_id_found = location_names[0][0]
        self.assertEqual(self.location_barcode_id, location_id_found)

    def test_20_location_search_by_name(self):
        """Search stock location by name"""
        location_names = self.location.name_search(name=self.name)
        location_ids_found = [location_name[0] for location_name in location_names]
        self.assertTrue(self.location_barcode_id in location_ids_found)

    def test_30_location_search_wo_results(self):
        """Search stock location without results"""
        location_names = self.location.name_search(name='nonexistent')
        self.assertFalse(location_names)
