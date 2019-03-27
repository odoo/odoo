# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form

from odoo.tests import common


class TestMrpAccount(common.TransactionCase):

    def setUp(self):
        super(TestMrpAccount, self).setUp()
        self.categ_standard = self.env['product.category'].create({'name': 'STANDARD',
                                                              'property_cost_method': 'standard',},)
        self.categ_real = self.env['product.category'].create({'name': 'REAL',
                                                          'property_cost_method': 'fifo',})
        self.categ_average = self.env['product.category'].create({'name': 'AVERAGE',
                                                             'property_cost_method': 'average'})
        self.dining_table = self.env.ref("mrp.product_product_computer_desk")
        self.dining_table.categ_id = self.categ_real.id
        self.product_table_sheet = self.env.ref('mrp.product_product_computer_desk_head')
        self.product_table_sheet.categ_id = self.categ_real.id
        self.product_table_leg = self.env.ref('mrp.product_product_computer_desk_leg')
        self.product_table_leg.categ_id = self.categ_average.id
        self.product_bolt = self.env.ref('mrp.product_product_computer_desk_bolt')
        self.product_bolt.categ_id = self.categ_standard.id
        self.source_location_id = self.ref('stock.stock_location_14')
        self.product_screw = self.env.ref('mrp.product_product_computer_desk_screw')
        self.product_screw.categ_id = self.categ_standard.id
        self.env['stock.move'].search([('product_id', 'in', [self.product_bolt.id, self.product_screw.id])])._do_unreserve()
        (self.product_bolt + self.product_screw).write({'type': 'product'})
        self.product_desk = self.env.ref('mrp.product_product_computer_desk')
        self.product_desk.tracking = 'none'

    def test_00_production_order_with_accounting(self):
        self.product_table_sheet.standard_price = 20.0
        self.product_table_leg.standard_price = 15.0
        self.product_bolt.standard_price = 10.0
        self.product_table_leg.tracking = 'none'
        self.product_table_sheet.tracking = 'none'
        inventory = self.env['stock.inventory'].create({
            'name': 'Inventory Product Table',
            'filter': 'partial',
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
        bom = self.env.ref('mrp.mrp_bom_desk').copy()
        bom.routing_id = False # TODO: extend the test later with the necessary operations
        production_table_form = Form(self.env['mrp.production'])
        production_table_form.product_id = self.dining_table
        production_table_form.bom_id = bom
        production_table_form.product_qty = 5.0
        production_table = production_table_form.save()

        production_table.action_confirm()

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production_table.id,
            'active_ids': [production_table.id],
        }))
        produce_form.qty_producing = 1.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        production_table.post_inventory()
        move_value = production_table.move_finished_ids.filtered(lambda x: x.state == "done").value

        # 1 table head at 20 + 4 table leg at 15 + 4 bolt at 10 + 10 screw at 10
        self.assertEqual(move_value, 121, 'Thing should have the correct price')

#        produce_wizard = self.env['mrp.product.produce'].with_context({
#            'active_id': production_table.id,
#            'active_ids': [production_table.id],
#        }).create({
#            'product_qty': 2.0,
#        })
#        produce_wizard.do_produce()
#        production_table.post_inventory()
#        move_value = production_table.move_finished_ids.filtered(lambda x: x.state == "done" and x.product_qty == 2.0).value
#        # 2 * Real price of the head (quant: 20) + standard price screw (product: 20*10) + standard price bolt (product: 8*10)
#        self.assertEqual(move_value, 280, 'Thing should have the correct price')
