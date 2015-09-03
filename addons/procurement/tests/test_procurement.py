# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.tests import common


class TestsProcurement(common.TransactionCase):

    def test_procurement(self):
        # I create a procurement
        self.procurement_order0 = self.env['procurement.order'].create({
            'name': 'Procurement Test',
            'company_id': self.ref('base.main_company'),
            'product_id': self.ref('product.product_product_32'),
            'product_qty': 15.0,
            'product_uom': self.ref('product.product_uom_unit'),
        })

        # I run the scheduler.
        self.procurement_order0.run_scheduler()

        # I check that procurement order is in exception, as at first there isn't any suitable rule
        self.assertEqual(self.procurement_order0.state, 'exception', "procurement order is in exception")
