# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestStockLandedCostsRounding(TestStockLandedCostsCommon):

    def test_stock_landed_costs_rounding(self):
        # In order to test the rounding in landed costs feature of stock, I create 2 landed cost

        # Define undivisible units
        product_uom_unit_round_1 = self.env.ref('uom.product_uom_unit')
        product_uom_unit_round_1.write({
            'name': 'Undivisible Units',
            'rounding': 1.0,
        })

        # I create 2 products with different cost prices and configure them for real_time
        # valuation and real price costing method
        product_landed_cost_3 = self.env['product.product'].create({
            'name': "LC product 3",
            'uom_id': product_uom_unit_round_1.id,
        })
        product_landed_cost_3.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        product_landed_cost_3.product_tmpl_id.categ_id.property_stock_account_input_categ_id = self.company_data['default_account_expense']
        product_landed_cost_3.product_tmpl_id.categ_id.property_stock_account_output_categ_id = self.company_data['default_account_revenue']

        product_landed_cost_4 = self.env['product.product'].create({
            'name': "LC product 4",
            'uom_id': product_uom_unit_round_1.id,
        })
        product_landed_cost_4.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        product_landed_cost_4.product_tmpl_id.categ_id.property_valuation = 'real_time'
        product_landed_cost_4.product_tmpl_id.categ_id.property_stock_account_input_categ_id = self.company_data['default_account_expense']
        product_landed_cost_4.product_tmpl_id.categ_id.property_stock_account_output_categ_id = self.company_data['default_account_revenue']

        picking_default_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))

        # I create 2 pickings moving those products
        vals = dict(picking_default_vals, **{
            'name': 'LC_pick_3',
            'picking_type_id': self.warehouse.in_type_id.id,
            'move_ids': [(0, 0, {
                'product_id': product_landed_cost_3.id,
                'product_uom_qty': 13,
                'product_uom': product_uom_unit_round_1.id,
                'location_id': self.ref('stock.stock_location_customers'),
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })],
        })
        picking_landed_cost_3 = self.env['stock.picking'].new(vals)
        picking_landed_cost_3._onchange_picking_type()
        picking_landed_cost_3.move_ids._onchange_product_id()
        picking_landed_cost_3.move_ids.name = 'move 3'
        vals = picking_landed_cost_3._convert_to_write(picking_landed_cost_3._cache)
        picking_landed_cost_3 = self.env['stock.picking'].create(vals)

        vals = dict(picking_default_vals, **{
            'name': 'LC_pick_4',
            'picking_type_id': self.warehouse.in_type_id.id,
            'move_ids': [(0, 0, {
                'product_id': product_landed_cost_4.id,
                'product_uom_qty': 1,
                'product_uom': self.ref('uom.product_uom_dozen'),
                'location_id': self.ref('stock.stock_location_customers'),
                'location_dest_id': self.warehouse.lot_stock_id.id,
                'price_unit': 17.00 / 12.00,
            })],
        })
        picking_landed_cost_4 = self.env['stock.picking'].new(vals)
        picking_landed_cost_4._onchange_picking_type()
        picking_landed_cost_4.move_ids._onchange_product_id()
        picking_landed_cost_4.move_ids.name = 'move 4'
        vals = picking_landed_cost_4._convert_to_write(picking_landed_cost_4._cache)
        picking_landed_cost_4 = self.env['stock.picking'].create(vals)

        # We perform all the tests for LC_pick_3
        # I receive picking LC_pick_3, and check how many quants are created
        picking_landed_cost_3.move_ids.price_unit = 1.0
        picking_landed_cost_3.action_confirm()
        picking_landed_cost_3.action_assign()
        picking_landed_cost_3._action_done()

        virtual_interior_design = self.env['product.product'].create({'name': 'Virtual Interior Design'})

        # I create a landed cost for picking 3
        default_vals = self.env['stock.landed.cost'].default_get(list(self.env['stock.landed.cost'].fields_get()))
        default_vals.update({
            'picking_ids': [picking_landed_cost_3.id],
            'account_journal_id': self.expenses_journal,
            'cost_lines': [(0, 0, {'product_id': virtual_interior_design.id})],
            'valuation_adjustment_lines': [],
        })
        stock_landed_cost_2 = self.env['stock.landed.cost'].new(default_vals)
        stock_landed_cost_2.cost_lines.onchange_product_id()
        stock_landed_cost_2.cost_lines.name = 'equal split'
        stock_landed_cost_2.cost_lines.split_method = 'equal'
        stock_landed_cost_2.cost_lines.price_unit = 15
        vals = stock_landed_cost_2._convert_to_write(stock_landed_cost_2._cache)
        stock_landed_cost_2 = self.env['stock.landed.cost'].create(vals)

        # I compute the landed cost using Compute button
        stock_landed_cost_2.compute_landed_cost()

        # I check the valuation adjustment lines
        for valuation in stock_landed_cost_2.valuation_adjustment_lines:
            self.assertEqual(valuation.additional_landed_cost, 15)

        # I confirm the landed cost
        stock_landed_cost_2.button_validate()

        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(stock_landed_cost_2.state, 'done')
        self.assertTrue(stock_landed_cost_2.account_move_id)

        # We perform all the tests for LC_pick_4
        # I receive picking LC_pick_4, and check how many quants are created
        picking_landed_cost_4.move_ids.price_unit = 17.0/12.0
        picking_landed_cost_4.action_confirm()
        picking_landed_cost_4.action_assign()
        picking_landed_cost_4._action_done()

        # I create a landed cost for picking 4
        default_vals = self.env['stock.landed.cost'].default_get(list(self.env['stock.landed.cost'].fields_get()))
        default_vals.update({
            'picking_ids': [picking_landed_cost_4.id],
            'account_journal_id': self.expenses_journal,
            'cost_lines': [(0, 0, {'product_id': virtual_interior_design.id})],
            'valuation_adjustment_lines': [],
        })
        stock_landed_cost_3 = self.env['stock.landed.cost'].new(default_vals)
        stock_landed_cost_3.cost_lines.onchange_product_id()
        stock_landed_cost_3.cost_lines.name = 'equal split'
        stock_landed_cost_3.cost_lines.split_method = 'equal'
        stock_landed_cost_3.cost_lines.price_unit = 11
        vals = stock_landed_cost_3._convert_to_write(stock_landed_cost_3._cache)
        stock_landed_cost_3 = self.env['stock.landed.cost'].create(vals)

        # I compute the landed cost using Compute button
        stock_landed_cost_3.compute_landed_cost()

        # I check the valuation adjustment lines
        for valuation in stock_landed_cost_3.valuation_adjustment_lines:
            self.assertEqual(valuation.additional_landed_cost, 11)

        # I confirm the landed cost
        stock_landed_cost_3.button_validate()

        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(stock_landed_cost_3.state, 'done')
        self.assertTrue(stock_landed_cost_3.account_move_id)

    def test_stock_landed_costs_rounding_02(self):
        """ The landed costs should be correctly computed, even when the decimal accuracy
        of the deciaml price is increased. """
        self.env.ref("product.decimal_price").digits = 4

        fifo_pc = self.env['product.category'].create({
            'name': 'Fifo Category',
            'parent_id': self.env.ref("product.product_category_all").id,
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
        })

        products = self.Product.create([{
            'name': 'Super Product %s' % price,
            'categ_id': fifo_pc.id,
            'type': 'product',
            'standard_price': price,
        } for price in [0.91, 0.93, 75.17, 20.54]])

        landed_product = self.Product.create({
            'name': 'Landed Costs',
            'type': 'service',
            'landed_cost_ok': True,
            'split_method_landed_cost': 'by_quantity',
            'standard_price': 1000.0,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_qty': qty,
                'price_unit': product.standard_price,
            }) for product, qty in zip(products, [6, 6, 3, 6])]
        })
        po.button_confirm()

        res_dict = po.picking_ids.button_validate()
        validate_wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict.get('context'))).save()
        validate_wizard.process()

        lc_form = Form(self.LandedCost)
        lc_form.picking_ids.add(po.picking_ids)
        with lc_form.cost_lines.new() as line:
            line.product_id = landed_product
        lc = lc_form.save()
        lc.compute_landed_cost()

        self.assertEqual(sum(lc.valuation_adjustment_lines.mapped('additional_landed_cost')), 1000.0)

    def test_stock_landed_costs_rounding_03(self):
        """
        Storable AVCO product
        Receive:
            5 @ 5
            5 @ 8
            5 @ 7
            20 @ 7.33
        Add landed cost of $5 to each receipt (except the first one)
        Deliver:
            23
            2
            10
        At the end, the SVL value should be zero
        """
        self.product_a.type = 'product'
        self.product_a.categ_id.property_cost_method = 'average'

        stock_location = self.warehouse.lot_stock_id
        supplier_location_id = self.ref('stock.stock_location_suppliers')
        customer_location_id = self.ref('stock.stock_location_customers')

        receipts = self.env['stock.picking'].create([{
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': supplier_location_id,
            'location_dest_id': stock_location.id,
            'move_ids': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'price_unit': price,
                'product_uom': self.product_a.uom_id.id,
                'product_uom_qty': qty,
                'location_id': supplier_location_id,
                'location_dest_id': stock_location.id,
            })]
        } for qty, price in [
            (5, 5.0),
            (5, 8.0),
            (5, 7.0),
            (20, 7.33),
        ]])

        receipts.action_confirm()
        for m in receipts.move_ids:
            m.quantity_done = m.product_uom_qty
        receipts.button_validate()

        landed_costs = self.env['stock.landed.cost'].create([{
            'picking_ids': [(6, 0, picking.ids)],
            'account_journal_id': self.expenses_journal.id,
            'cost_lines': [(0, 0, {
                'name': 'equal split',
                'split_method': 'equal',
                'price_unit': 5.0,
                'product_id': self.landed_cost.id
            })],
        } for picking in receipts[1:]])
        landed_costs.compute_landed_cost()
        landed_costs.button_validate()

        self.assertEqual(self.product_a.standard_price, 7.47)

        deliveries = self.env['stock.picking'].create([{
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location_id,
            'move_ids': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom': self.product_a.uom_id.id,
                'product_uom_qty': qty,
                'location_id': stock_location.id,
                'location_dest_id': customer_location_id,
            })]
        } for qty in [23, 2, 10]])

        deliveries.action_confirm()
        for m in deliveries.move_ids:
            m.quantity_done = m.product_uom_qty
        deliveries.button_validate()

        self.assertEqual(self.product_a.value_svl, 0)
