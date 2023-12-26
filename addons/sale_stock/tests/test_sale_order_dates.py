# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from datetime import timedelta
from odoo import fields
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestSaleExpectedDate(ValuationReconciliationTestCommon):

    def test_sale_order_expected_date(self):
        """ Test expected date and effective date of Sales Orders """
        Product = self.env['product.product']

        product_A = Product.create({
            'name': 'Product A',
            'type': 'product',
            'sale_delay': 5,
            'uom_id': 1,
        })
        product_B = Product.create({
            'name': 'Product B',
            'type': 'product',
            'sale_delay': 10,
            'uom_id': 1,
        })
        product_C = Product.create({
            'name': 'Product C',
            'type': 'product',
            'sale_delay': 15,
            'uom_id': 1,
        })

        self.env['stock.quant']._update_available_quantity(product_A, self.company_data['default_warehouse'].lot_stock_id, 10)
        self.env['stock.quant']._update_available_quantity(product_B, self.company_data['default_warehouse'].lot_stock_id, 10)
        self.env['stock.quant']._update_available_quantity(product_C, self.company_data['default_warehouse'].lot_stock_id, 10)

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A Customer'}).id,
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': product_A.name, 'product_id': product_A.id, 'customer_lead': product_A.sale_delay, 'product_uom_qty': 5}),
                (0, 0, {'name': product_B.name, 'product_id': product_B.id, 'customer_lead': product_B.sale_delay, 'product_uom_qty': 5}),
                (0, 0, {'name': product_C.name, 'product_id': product_C.id, 'customer_lead': product_C.sale_delay, 'product_uom_qty': 5})
            ],
        })

        # if Shipping Policy is set to `direct`(when SO is in draft state) then expected date should be
        # current date + shortest lead time from all of it's order lines
        expected_date = fields.Datetime.now() + timedelta(days=5)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        # if Shipping Policy is set to `one`(when SO is in draft state) then expected date should be
        # current date + longest lead time from all of it's order lines
        sale_order.write({'picking_policy': 'one'})
        expected_date = fields.Datetime.now() + timedelta(days=15)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        sale_order.action_confirm()

        # Setting confirmation date of SO to 5 days from today so that the expected/effective date could be checked
        # against real confirmation date
        confirm_date = fields.Datetime.now() + timedelta(days=5)
        sale_order.write({'date_order': confirm_date})

        # if Shipping Policy is set to `one`(when SO is confirmed) then expected date should be
        # SO confirmation date + longest lead time from all of it's order lines
        expected_date = confirm_date + timedelta(days=15)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        # if Shipping Policy is set to `direct`(when SO is confirmed) then expected date should be
        # SO confirmation date + shortest lead time from all of it's order lines
        sale_order.write({'picking_policy': 'direct'})
        expected_date = confirm_date + timedelta(days=5)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        # Check effective date, it should be date on which the first shipment successfully delivered to customer
        picking = sale_order.picking_ids[0]
        for ml in picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        picking._action_done()
        self.assertEqual(picking.state, 'done', "Picking not processed correctly!")
        self.assertEqual(fields.Date.context_today(sale_order), sale_order.effective_date, "Wrong effective date on sale order!")

    def test_sale_order_commitment_date(self):

        # In order to test the Commitment Date feature in Sales Orders in Odoo,
        # I copy a demo Sales Order with committed Date on 2010-07-12
        new_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'A Partner'}).id,
            'order_line': [(0, 0, {
                'name': "A product",
                'product_id': self.env['product.product'].create({
                    'name': 'A product',
                    'type': 'product',
                }).id,
                'product_uom_qty': 1,
                'price_unit': 750,
            })],
            'commitment_date': '2010-07-12',
        })
        # I confirm the Sales Order.
        new_order.action_confirm()
        # I verify that the Procurements and Stock Moves have been generated with the correct date
        security_delay = timedelta(days=new_order.company_id.security_lead)
        commitment_date = fields.Datetime.from_string(new_order.commitment_date)
        right_date = commitment_date - security_delay
        for line in new_order.order_line:
            self.assertEqual(line.move_ids[0].date, right_date, "The expected date for the Stock Move is wrong")
