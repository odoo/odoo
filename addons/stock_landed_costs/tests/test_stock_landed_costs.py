# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestStockLandedCosts(TestStockLandedCostsCommon):

    def test_stock_landed_costs(self):
        # In order to test the landed costs feature of stock,
        # I create a landed cost, confirm it and check its account move created

        # I create 2 products with different volume and gross weight and configure
        # them for real_time valuation and fifo costing method
        product_landed_cost_1 = self.env['product.product'].create({
            'name': "LC product 1",
            'weight': 10,
            'volume': 1,
            'categ_id': self.stock_account_product_categ.id,
            'type': 'product',
        })

        product_landed_cost_2 = self.env['product.product'].create({
            'name': "LC product 2",
            'weight': 20,
            'volume': 1.5,
            'categ_id': self.stock_account_product_categ.id,
            'type': 'product',
        })

        self.assertEqual(product_landed_cost_1.value_svl, 0)
        self.assertEqual(product_landed_cost_1.quantity_svl, 0)
        self.assertEqual(product_landed_cost_2.value_svl, 0)
        self.assertEqual(product_landed_cost_2.quantity_svl, 0)

        picking_default_vals = self.env['stock.picking'].default_get(list(self.env['stock.picking'].fields_get()))

        # I create 2 picking moving those products
        vals = dict(picking_default_vals, **{
            'name': 'LC_pick_1',
            'picking_type_id': self.warehouse.out_type_id.id,
            'move_lines': [(0, 0, {
                'product_id': product_landed_cost_1.id,
                'product_uom_qty': 5,
                'product_uom': self.ref('uom.product_uom_unit'),
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        picking_landed_cost_1 = self.env['stock.picking'].new(vals)
        picking_landed_cost_1._onchange_picking_type()
        picking_landed_cost_1.move_lines._onchange_product_id()
        picking_landed_cost_1.move_lines.name = 'move 1'
        vals = picking_landed_cost_1._convert_to_write(picking_landed_cost_1._cache)
        picking_landed_cost_1 = self.env['stock.picking'].create(vals)

        # Confirm and assign picking
        self.env.company.anglo_saxon_accounting = True
        picking_landed_cost_1.action_confirm()
        picking_landed_cost_1.action_assign()
        picking_landed_cost_1.move_lines.quantity_done = 5
        picking_landed_cost_1.button_validate()

        vals = dict(picking_default_vals, **{
            'name': 'LC_pick_2',
            'picking_type_id': self.warehouse.out_type_id.id,
            'move_lines': [(0, 0, {
                'product_id': product_landed_cost_2.id,
                'product_uom_qty': 10,
                'product_uom': self.ref('uom.product_uom_unit'),
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        picking_landed_cost_2 = self.env['stock.picking'].new(vals)
        picking_landed_cost_2._onchange_picking_type()
        picking_landed_cost_2.move_lines._onchange_product_id()
        picking_landed_cost_2.move_lines.name = 'move 2'
        vals = picking_landed_cost_2._convert_to_write(picking_landed_cost_2._cache)
        picking_landed_cost_2 = self.env['stock.picking'].create(vals)

        # Confirm and assign picking
        picking_landed_cost_2.action_confirm()
        picking_landed_cost_2.action_assign()
        picking_landed_cost_2.move_lines.quantity_done = 10
        picking_landed_cost_2.button_validate()

        self.assertEqual(product_landed_cost_1.value_svl, 0)
        self.assertEqual(product_landed_cost_1.quantity_svl, -5)
        self.assertEqual(product_landed_cost_2.value_svl, 0)
        self.assertEqual(product_landed_cost_2.quantity_svl, -10)

        # I create a landed cost for those 2 pickings
        default_vals = self.env['stock.landed.cost'].default_get(list(self.env['stock.landed.cost'].fields_get()))
        virtual_home_staging = self.env['product.product'].create({
            'name': 'Virtual Home Staging',
            'categ_id': self.stock_account_product_categ.id,
        })
        default_vals.update({
            'picking_ids': [picking_landed_cost_1.id, picking_landed_cost_2.id],
            'account_journal_id': self.expenses_journal,
            'cost_lines': [
                (0, 0, {'product_id': virtual_home_staging.id}),
                (0, 0, {'product_id': virtual_home_staging.id}),
                (0, 0, {'product_id': virtual_home_staging.id}),
                (0, 0, {'product_id': virtual_home_staging.id})],
            'valuation_adjustment_lines': [],
        })
        cost_lines_values = {
            'name': ['equal split', 'split by quantity', 'split by weight', 'split by volume'],
            'split_method': ['equal', 'by_quantity', 'by_weight', 'by_volume'],
            'price_unit': [10, 150, 250, 20],
        }
        stock_landed_cost_1 = self.env['stock.landed.cost'].new(default_vals)
        for index, cost_line in enumerate(stock_landed_cost_1.cost_lines):
            cost_line.onchange_product_id()
            cost_line.name = cost_lines_values['name'][index]
            cost_line.split_method = cost_lines_values['split_method'][index]
            cost_line.price_unit = cost_lines_values['price_unit'][index]
        vals = stock_landed_cost_1._convert_to_write(stock_landed_cost_1._cache)
        stock_landed_cost_1 = self.env['stock.landed.cost'].create(vals)

        # I compute the landed cost  using Compute button
        stock_landed_cost_1.compute_landed_cost()

        # I check the valuation adjustment lines
        for valuation in stock_landed_cost_1.valuation_adjustment_lines:
            if valuation.cost_line_id.name == 'equal split':
                self.assertEqual(valuation.additional_landed_cost, 5)
            elif valuation.cost_line_id.name == 'split by quantity' and valuation.move_id.name == "move 1":
                self.assertEqual(valuation.additional_landed_cost, 50)
            elif valuation.cost_line_id.name == 'split by quantity' and valuation.move_id.name == "move 2":
                self.assertEqual(valuation.additional_landed_cost, 100)
            elif valuation.cost_line_id.name == 'split by weight' and valuation.move_id.name == "move 1":
                self.assertEqual(valuation.additional_landed_cost, 50)
            elif valuation.cost_line_id.name == 'split by weight' and valuation.move_id.name == "move 2":
                self.assertEqual(valuation.additional_landed_cost, 200)
            elif valuation.cost_line_id.name == 'split by volume' and valuation.move_id.name == "move 1":
                self.assertEqual(valuation.additional_landed_cost, 5)
            elif valuation.cost_line_id.name == 'split by volume' and valuation.move_id.name == "move 2":
                self.assertEqual(valuation.additional_landed_cost, 15)
            else:
                raise ValidationError('unrecognized valuation adjustment line')

        # I confirm the landed cost
        stock_landed_cost_1.button_validate()

        # I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(stock_landed_cost_1.state, "done")
        self.assertTrue(stock_landed_cost_1.account_move_id)
        self.assertEqual(len(stock_landed_cost_1.account_move_id.line_ids), 48)

        lc_value = sum(stock_landed_cost_1.account_move_id.line_ids.filtered(lambda aml: aml.account_id.name.startswith('Expenses')).mapped('debit'))
        product_value = abs(product_landed_cost_1.value_svl) + abs(product_landed_cost_2.value_svl)
        self.assertEqual(lc_value, product_value)

        self.assertEqual(len(picking_landed_cost_1.move_lines.stock_valuation_layer_ids), 5)
        self.assertEqual(len(picking_landed_cost_2.move_lines.stock_valuation_layer_ids), 5)

    def test_aml_account_selection(self):
        """
        Process a PO with a landed cost, then create and post the bill. The
        account of the landed cost AML should be:
        - Expense if the categ valuation is manual
        - Stock IN if the categ valuation is real time
        """
        self.landed_cost.landed_cost_ok = True

        for valuation, account in [
            ('manual_periodic', self.company_data['default_account_expense']),
            ('real_time', self.env.company.property_stock_account_input_categ_id),
        ]:
            self.landed_cost.categ_id.property_valuation = valuation
            po = self.env['purchase.order'].create({
                'partner_id': self.partner_a.id,
                'currency_id': self.company_data['currency'].id,
                'order_line': [
                    (0, 0, {
                        'name': self.product_a.name,
                        'product_id': self.product_a.id,
                        'product_qty': 1.0,
                        'product_uom': self.product_a.uom_po_id.id,
                        'price_unit': 100.0,
                        'taxes_id': False,
                    }),
                    (0, 0, {
                        'name': self.landed_cost.name,
                        'product_id': self.landed_cost.id,
                        'product_qty': 1.0,
                        'price_unit': 100.0,
                    }),
                ],
            })
            po.button_confirm()

            receipt = po.picking_ids
            receipt.move_lines.quantity_done = 1
            receipt.button_validate()
            po.order_line[1].qty_received = 1

            po.action_create_invoice()
            bill = po.invoice_ids
            bill.invoice_date = fields.Date.today()
            bill._post()

            landed_cost_aml = bill.invoice_line_ids.filtered(lambda l: l.product_id == self.landed_cost)
            self.assertEqual(bill.state, 'posted', 'Incorrect value with valuation %s' % valuation)
            self.assertEqual(landed_cost_aml.account_id, account, 'Incorrect value with valuation %s' % valuation)
