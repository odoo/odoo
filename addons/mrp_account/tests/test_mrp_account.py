# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.test_workorder_operation import TestWorkOrderProcessCommon
from odoo.tests import Form


class TestMrpAccount(TestWorkOrderProcessCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMrpAccount, cls).setUpClass()

        cls.categ_standard = cls.env['product.category'].create({
            'name': 'STANDARD',
            'property_cost_method': 'standard'
        })
        cls.categ_real = cls.env['product.category'].create({
            'name': 'REAL',
            'property_cost_method': 'fifo'
        })
        cls.categ_average = cls.env['product.category'].create({
            'name': 'AVERAGE',
            'property_cost_method': 'average'
        })
        cls.dining_table.categ_id = cls.categ_real.id
        cls.product_table_sheet.categ_id = cls.categ_real.id
        cls.product_table_leg.categ_id = cls.categ_average.id
        cls.product_bolt.categ_id = cls.categ_standard.id
        cls.product_screw.categ_id = cls.categ_standard.id
        cls.env['stock.move'].search([('product_id', 'in', [cls.product_bolt.id, cls.product_screw.id])])._do_unreserve()
        (cls.product_bolt + cls.product_screw).write({'type': 'product'})
        cls.dining_table.tracking = 'none'

    def test_00_production_order_with_accounting(self):
        self.product_table_sheet.standard_price = 20.0
        self.product_table_leg.standard_price = 15.0
        self.product_bolt.standard_price = 10.0
        self.product_screw.standard_price = 0.1
        self.product_table_leg.tracking = 'none'
        self.product_table_sheet.tracking = 'none'
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'line_ids': [(0, 0, {
                'product_id': self.product_table_sheet.id,  # tracking serial
                'product_uom_id': self.product_table_sheet.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': self.product_table_leg.id,  # tracking lot
                'product_uom_id': self.product_table_leg.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': self.product_bolt.id,
                'product_uom_id': self.product_bolt.uom_id.id,
                'product_qty': 20,
                'location_id': self.source_location_id
            }), (0, 0, {
                'product_id': self.product_screw.id,
                'product_uom_id': self.product_screw.uom_id.id,
                'product_qty': 200000,
                'location_id': self.source_location_id
            }),
            ]
        })
        inventory.action_validate
        bom = self.mrp_bom_desk.copy()
        bom.routing_id = False # TODO: extend the test later with the necessary operations
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = self.dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 5.0
        production_table = production_table_form.save()

        production_table.extra_cost = 20
        production_table.action_confirm()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production_table.id,
            'active_ids': [production_table.id],
        }))
        produce_form.qty_producing = 1.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        production_table.post_inventory()
        move_value = production_table.move_finished_ids.filtered(lambda x: x.state == "done").stock_valuation_layer_ids.value

        # 1 table head at 20 + 4 table leg at 15 + 4 bolt at 10 + 10 screw at 10 + 1*20 (extra cost)
        self.assertEqual(move_value, 141, 'Thing should have the correct price')
