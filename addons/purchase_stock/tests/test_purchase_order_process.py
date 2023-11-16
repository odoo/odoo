from odoo import Command, fields
from odoo.tests import tagged
from .common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestPurchaseOrderProcess(PurchaseTestCommon):

    def test_00_cancel_purchase_order_flow(self):
        """ Test cancel purchase order with group user."""

        # In order to test the cancel flow,start it from canceling confirmed purchase order.
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
            'state': 'draft',
        })
        po_edit_with_user = purchase_order.with_user(self.res_users_purchase_user)

        # Confirm the purchase order.
        po_edit_with_user.button_confirm()

        # Check the "Approved" status  after confirmed RFQ.
        self.assertEqual(po_edit_with_user.state, 'purchase', 'Purchase: PO state should be "Purchase')

        # First cancel receptions related to this order if order shipped.
        po_edit_with_user.picking_ids.action_cancel()

        # Able to cancel purchase order.
        po_edit_with_user.button_cancel()

        # Check that order is cancelled.
        self.assertEqual(po_edit_with_user.state, 'cancel', 'Purchase: PO state should be "Cancel')

    def test_01_packaging_propagation(self):
        """Create a PO with lines using packaging, check the packaging propagate
        to its move.
        """
        product = self.env['product.product'].create({
            'name': 'Product with packaging',
            'type': 'product',
        })

        packaging = self.env['product.packaging'].create({
            'name': 'box',
            'product_id': product.id,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_qty': 1.0,
                    'product_uom': product.uom_id.id,
                    'product_packaging_id': packaging.id,
                })],
        })
        po.button_confirm()
        self.assertEqual(po.order_line.move_ids.product_packaging_id, packaging)

    def test_analytic_distribution_propagation_with_exchange_difference(self):
        # Create 2 rates in order to generate an exchange difference later.
        eur = self.env.ref('base.EUR')
        eur.write({
            'rate_ids': [
                Command.clear(),
                Command.create({
                    'name': fields.Date.from_string('2023-01-01'),
                    'company_rate': 2.0,
                }),
                Command.create({
                    'name': fields.Date.from_string('2023-12-01'),
                    'company_rate': 3.0,
                }),
            ],
            'active': True,
        })

        # Create a mandatory analytic account.
        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Analytic Plan',
            'default_applicability': 'mandatory',
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Analytic Account',
            'plan_id': analytic_plan.id},
        )

        # Create a storable product with FIFO costing method and automated inventory valuation.
        analytic_product_category = self.env['product.category'].create({
            'name': 'Analytic Product Category',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        analytic_product = self.env['product.product'].create({
            'name': 'Analytic Product',
            'detailed_type': 'product',
            'categ_id': analytic_product_category.id,
            'lst_price': 100.0,
            'standard_price': 25.0,
        })

        # Create and confirm a Purchase Order using aforementioned product and currency.
        purchase_order = self.env['purchase.order'].create({
            'date_order': fields.Date.from_string('2023-12-04'),
            'currency_id': eur.id,
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': analytic_product.id,
                    'product_qty': 10.0,
                    'analytic_distribution': {analytic_account.id: 100},
                }),
            ],
        })
        purchase_order.button_confirm()

        # Make sure a stock move has been created to replenish the product.
        self.assertEqual(len(purchase_order.picking_ids.move_ids), 1)

        stock_move = purchase_order.picking_ids.move_ids
        stock_move.quantity = stock_move.product_uom_qty

        purchase_order.picking_ids.button_validate()
        purchase_order.action_create_invoice()

        # Make sure a first Journal Entry has been created (to account for the stock move).
        self.assertEqual(len(stock_move.account_move_ids), 1)
        stock_account_move = stock_move.account_move_ids

        # Make sure the Vendor Bill has been created,
        # and confirm it at an earlier date (to generate the exchange difference).
        self.assertEqual(len(purchase_order.invoice_ids), 1)

        vendor_bill = purchase_order.invoice_ids
        vendor_bill.invoice_date = fields.Date.from_string('2023-11-01')
        vendor_bill.action_post()

        # Make sure a second Journal Entry has been created (to account for the exchange difference).
        self.assertEqual(len(stock_move.account_move_ids), 2)
        exchange_account_move = stock_move.account_move_ids - stock_account_move

        # Make sure both exchange Journal Items have the correct analytic distribution.
        self.assertEqual(len(exchange_account_move.line_ids), 2)
        for line in exchange_account_move.line_ids:
            self.assertTrue(line.analytic_distribution)
            self.assertEqual(line.analytic_distribution[str(analytic_account.id)], 100)
