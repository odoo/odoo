# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


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

    def test_kit_cost_repartition(self):
        """ Receive a BoM with components in fifo valuation. Check the price
        unit and the value on the moves after the confirmation and validation.
        """
        bom = self.env.ref('mrp.mrp_bom_wood_panel')
        bom.type = 'phantom'
        bom.bom_line_ids[0].cost_repartition = 40
        bom.bom_line_ids[1].cost_repartition = 60
        bom.bom_line_ids.mapped('product_id.categ_id').write({'property_cost_method': 'fifo'})

        product_kit = bom.product_tmpl_id.product_variant_id

        move = self.env['stock.move'].create({
            'name': product_kit.name,
            'product_id': product_kit.id,
            'product_uom_qty': 5,
            'product_uom': product_kit.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'price_unit': 100,
        })

        moves = move._action_confirm()
        self.assertEqual(len(moves), 2)
        move_with_40 = moves.filtered(lambda m: m.product_id == bom.bom_line_ids[0].product_id)
        move_with_60 = moves.filtered(lambda m: m.product_id == bom.bom_line_ids[1].product_id)

        self.assertEqual(move_with_40.price_unit, 40)
        self.assertEqual(move_with_60.price_unit, 60)

        moves.write({'quantity_done': 5})
        moves._action_done()
        self.assertEqual(sum(move_with_40.stock_valuation_layer_ids.mapped('value')), 200)
        self.assertEqual(sum(move_with_60.stock_valuation_layer_ids.mapped('value')), 300)

    def test_byproduct_cost_repartition(self):
        """ Manufacturing order with byproduct using cost_repartition. Check
        value on move in order to ensure that cost repartition was correctly
        apply.
        """
        byproduct_1 = self.env['product.product'].create({
            'name': 'wood chips',
            'categ_id': self.categ_real.id,
        })
        byproduct_2 = self.env['product.product'].create({
            'name': 'fingers',
            'categ_id': self.categ_real.id,
        })
        bom = self.env.ref('mrp.mrp_bom_wood_panel')
        product = bom.product_tmpl_id.product_variant_id
        bom.cost_repartition = 45
        self.env['mrp.bom.byproduct'].create({
            'product_id': byproduct_1.id,
            'product_uom_id': byproduct_1.uom_id.id,
            'product_qty': 10,
            'cost_repartition': 30,
            'bom_id': bom.id,
        })
        self.env['mrp.bom.byproduct'].create({
            'product_id': byproduct_2.id,
            'product_uom_id': byproduct_2.uom_id.id,
            'product_qty': 5,
            'cost_repartition': 25,
            'bom_id': bom.id,
        })
        production_order_form = Form(self.env['mrp.production'])
        production_order_form.product_id = product
        production_order_form.bom_id = bom
        production_order_form.product_qty = 5.0
        production_order = production_order_form.save()
        production_order.action_confirm()
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production_order.id,
            'active_ids': [production_order.id],
        }))
        produce_form.qty_producing = 5.0
        produce_wizard = produce_form.save()
        produce_wizard.do_produce()
        production_order.button_mark_done()

        byproduct_1_move = production_order.move_finished_ids.filtered(lambda m: m.product_id == byproduct_1)
        byproduct_2_move = production_order.move_finished_ids.filtered(lambda m: m.product_id == byproduct_2)
        finished_product_move = production_order.move_finished_ids.filtered(lambda m: m.product_id == production_order.product_id)

        # Total cost of the product is 200
        # byproduct_1 cost repartition = 30 -> 200 * 30 /100 = 60
        self.assertEqual(sum(byproduct_1_move.stock_valuation_layer_ids.mapped('value')), 60.0)
        # byproduct_2 cost repartition = 25 -> 200 * 25 /100 = 50
        self.assertEqual(sum(byproduct_2_move.stock_valuation_layer_ids.mapped('value')), 50.0)
        # Finished product use its standard price since its valuation is standard
        self.assertEqual(product.categ_id.property_cost_method, 'standard')
        # Default cost price = 80 * 5 = 400
        self.assertEqual(sum(finished_product_move.stock_valuation_layer_ids.mapped('value')), product.standard_price * 5)
