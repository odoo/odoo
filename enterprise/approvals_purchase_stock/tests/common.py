# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.approvals_purchase.tests import common


class TestApprovalsCommon(common.TestApprovalsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set the location as optional.
        cls.purchase_category.has_location = 'optional'
        # Creates two warehouses.
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse Test 1',
            'code': 'WH1',
            'sequence': 1,
        })
        cls.warehouse_2 = cls.env['stock.warehouse'].create({
            'name': 'Warehouse Test 2',
            'code': 'WH2',
            'sequence': 2,
        })
        cls.wh_picking_type_1 = cls.warehouse_1.in_type_id
        cls.wh_picking_type_2 = cls.warehouse_2.in_type_id
