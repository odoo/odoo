# -*- coding: utf-8 -*-

from odoo.tests import common


class TestStockLocationSearch(common.TransactionCase):
    def setUp(self):
        super(TestStockLocationSearch, self).setUp()
        self.location = self.env['stock.location']
        self.location_barcode = self.env.ref('stock.stock_location_3')
        self.location_barcode_id = self.location_barcode.id
        self.barcode = self.location_barcode.barcode
        self.name = self.location_barcode.name

    def test_10_location_search_by_barcode(self):
        """Search stock location by barcode"""
        location_names = self.location.name_search(name=self.barcode)
        self.assertEquals(len(location_names), 1)
        location_id_found = location_names[0][0]
        self.assertEquals(self.location_barcode_id, location_id_found)

    def test_20_location_search_by_name(self):
        """Search stock location by name"""
        location_names = self.location.name_search(name=self.name)
        location_ids_found = [location_name[0] for location_name in location_names]
        self.assertTrue(self.location_barcode_id in location_ids_found)

    def test_30_location_search_wo_results(self):
        """Search stock location without results"""
        location_names = self.location.name_search(name='nonexistent')
        self.assertFalse(location_names)
