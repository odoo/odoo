# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.mrp.tests.test_mrp_users import TestMrpUsers


class TestOrderDemo(TestMrpUsers):

    def setUp(self):
        super(TestOrderDemo, self).setUp()
        # I create Production Order of PC Assemble SC349 to produce 5.0 Unit.

        self.mrp_production_test1 = self.env['mrp.production'].sudo(self.res_users_mrp_user.id).create({
            'product_id': self.env.ref('product.product_product_3').id,
            'product_qty': 5.0,
            'location_src_id': self.env.ref('stock.stock_location_14').id,
            'location_dest_id': self.env.ref('stock.stock_location_output').id,
            'bom_id': self.env.ref('mrp.mrp_bom_9').id,
            'routing_id': self.env.ref('mrp.mrp_routing_1').id
        })
