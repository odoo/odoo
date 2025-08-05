# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


@tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
class TestAngloSaxonValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.company_id.anglo_saxon_accounting = True

        cls.product = cls.env['product.product'].create({
            'name': 'product',
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
        })

    def _inv_adj_two_units(self):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,  # tracking serial
            'inventory_quantity': 2,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        }).action_apply_inventory()

    def _so_and_confirm_two_units(self):
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'price_unit': 12,
                    'tax_ids': False,  # no love taxes amls
                })],
        })
        sale_order.flush_recordset()
        sale_order.action_confirm()
        return sale_order

    def _fifo_in_one_eight_one_ten(self):
        # Put two items in stock.
        in_move_1 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 8,
        })
        in_move_1._action_confirm()
        in_move_1.write({'quantity': 1, 'picked': True})
        in_move_1._action_done()
        in_move_2 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 10,
        })
        in_move_2._action_confirm()
        in_move_2.write({'quantity': 1, 'picked': True})
        in_move_2._action_done()

    # -------------------------------------------------------------------------
    # Standard Ordered
    # -------------------------------------------------------------------------
    def test_standard_ordered_invoice_pre_delivery(self):
        """Standard price set to 10. Get 2 units in stock. Sale order 2@12. Standard price set
        to 14. Invoice 2 without delivering. The amount in Stock OUT and COGS should be 14*2.
        """
        self.product.categ_id.property_cost_method = 'standard'
        self.product.invoice_policy = 'order'
        self.product.standard_price = 10.0

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # standard price to 14
        self.product.standard_price = 14.0

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 28)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 28)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_standard_ordered_invoice_post_partial_delivery_1(self):
        """Standard price set to 10. Get 2 units in stock. Sale order 2@12. Deliver 1, invoice 1,
        change the standard price to 14, deliver one, change the standard price to 16, invoice 1.
        The amounts used in Stock OUT and COGS should be 10 then 14."""
        self.product.categ_id.property_cost_method = 'standard'
        self.product.invoice_policy = 'order'
        self.product.standard_price = 10.0

        # Put two items in stock.
        sale_order = self._so_and_confirm_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # Invoice 1
        invoice = sale_order._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 1
        invoice_form.save()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids[0].move_ids.write({'quantity': 1, 'picked': True})
        sale_order.picking_ids[0].button_validate()

        # change the standard price to 16
        self.product.standard_price = 16.0

        # invoice 1
        invoice2 = sale_order._create_invoices()
        invoice2.action_post()
        amls = invoice2.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 14)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 14)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

    def test_standard_ordered_invoice_post_delivery(self):
        """Standard price set to 10. Get 2 units in stock. Sale order 2@12. Deliver 1, change the
        standard price to 14, deliver one, invoice 2. The amounts used in Stock OUT and COGS should
        be 12*2."""
        self.product.categ_id.property_cost_method = 'standard'
        self.product.invoice_policy = 'order'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids.filtered('backorder_id').move_ids.write({'quantity': 1, 'picked': True})
        sale_order.picking_ids.filtered('backorder_id').button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 24)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 24)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    # -------------------------------------------------------------------------
    # Standard Delivered
    # -------------------------------------------------------------------------
    def test_standard_delivered_invoice_pre_delivery(self):
        """Not possible to invoice pre delivery."""
        self.product.categ_id.property_cost_method = 'standard'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Invoice the sale order.
        # Nothing delivered = nothing to invoice.
        with self.assertRaises(UserError):
            sale_order._create_invoices()

    def test_standard_delivered_invoice_post_partial_delivery(self):
        """Standard price set to 10. Get 2 units in stock. Sale order 2@12. Deliver 1, invoice 1,
        change the standard price to 14, deliver one, change the standard price to 16, invoice 1.
        The amounts used in Stock OUT and COGS should be 10 then 14."""
        self.product.categ_id.property_cost_method = 'standard'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        # Put two items in stock.
        sale_order = self._so_and_confirm_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # Invoice 1
        invoice = sale_order._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 1
        invoice_form.save()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids[0].move_ids.write({'quantity': 1, 'picked': True})
        sale_order.picking_ids[0].button_validate()

        # change the standard price to 16
        self.product.standard_price = 16.0

        # invoice 1
        invoice2 = sale_order._create_invoices()
        invoice2.action_post()
        amls = invoice2.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 14)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 14)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

    def test_standard_delivered_invoice_post_delivery(self):
        """Standard price set to 10. Get 2 units in stock. Sale order 2@12. Deliver 1, change the
        standard price to 14, deliver one, invoice 2. The amounts used in Stock OUT and COGS should
        be 12*2."""
        self.product.categ_id.property_cost_method = 'standard'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids.filtered('backorder_id').move_ids.write({'quantity': 1, 'picked': True})
        sale_order.picking_ids.filtered('backorder_id').button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 24)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 24)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    # -------------------------------------------------------------------------
    # AVCO Ordered
    # -------------------------------------------------------------------------
    def test_avco_ordered_invoice_pre_delivery(self):
        """Standard price set to 10. Sale order 2@12. Invoice without delivering."""
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'order'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_avco_ordered_invoice_post_partial_delivery(self):
        """Standard price set to 10. Sale order 2@12. Invoice after delivering 1."""
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'order'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_avco_ordered_invoice_post_delivery(self):
        """Standard price set to 10. Sale order 2@12. Invoice after full delivery."""
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'order'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_avco_ordered_return_and_receipt(self):
        """ Sell and deliver some products before the user encodes the products receipt """
        product = self.product
        product.invoice_policy = 'order'
        product.is_storable = True
        product.categ_id.property_cost_method = 'average'
        product.categ_id.property_valuation = 'real_time'
        product.list_price = 100
        product.standard_price = 50

        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 5.0,
                'product_uom_id': product.uom_id.id,
                'price_unit': product.list_price})],
        })
        so.action_confirm()

        pick = so.picking_ids
        pick.move_ids.write({'quantity': 5, 'picked': True})
        pick.button_validate()

        product.standard_price = 40

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=pick.ids, active_id=pick.sorted().ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 1
        return_wiz.product_return_moves.to_refund = False
        res = return_wiz.action_create_returns()

        return_pick = self.env['stock.picking'].browse(res['res_id'])
        return_pick.move_ids.write({'quantity': 1, 'picked': True})
        return_pick.button_validate()

        picking = self.env['stock.picking'].create({
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'picking_type_id': self.company_data['default_warehouse'].in_type_id.id,
        })
        # We don't set the price_unit so that the `standard_price` will be used (see _get_price_unit()):
        self.env['stock.move'].create({
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'picking_id': picking.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'quantity': 1,
            'picked': True,
        })
        picking.button_validate()

        invoice = so._create_invoices()
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    # -------------------------------------------------------------------------
    # AVCO Delivered
    # -------------------------------------------------------------------------
    def test_avco_delivered_invoice_pre_delivery(self):
        """Standard price set to 10. Sale order 2@12. Invoice without delivering. """
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Invoice the sale order.
        # Nothing delivered = nothing to invoice.
        with self.assertRaises(UserError):
            sale_order._create_invoices()

    def test_avco_delivered_invoice_post_partial_delivery(self):
        """Standard price set to 10. Sale order 2@12. Invoice after delivering 1."""
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

    def test_avco_delivered_invoice_post_delivery(self):
        """Standard price set to 10. Sale order 2@12. Invoice after full delivery."""
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        # Put two items in stock.
        self._inv_adj_two_units()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()
        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_avco_partially_owned_and_delivered_invoice_post_delivery(self):
        """
        Standard price set to 10. Sale order 2@12. One of the delivered
        products was owned by an external partner. Invoice after full delivery.
        """
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        self.env['stock.quant']._update_available_quantity(self.product, self.company_data['default_warehouse'].lot_stock_id, 1, owner_id=self.partner_b)
        self.env['stock.quant']._update_available_quantity(self.product, self.company_data['default_warehouse'].lot_stock_id, 1)

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()
        # Deliver both products (there should be two SML)
        sale_order.picking_ids.move_line_ids.write({'quantity': 1, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Invoice one by one
        invoice01 = sale_order._create_invoices()
        with Form(invoice01) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 1
        invoice01.action_post()

        invoice02 = sale_order._create_invoices()
        invoice02.action_post()

        # COGS should ignore the owned product
        self.assertRecordValues(invoice01.line_ids, [
            # pylint: disable=bad-whitespace
            {'account_id': self.company_data['default_account_revenue'].id,     'debit': 0,     'credit': 12},
            {'account_id': self.company_data['default_account_receivable'].id,  'debit': 12,    'credit': 0},
            {'account_id': self.company_data['default_account_stock_out'].id,   'debit': 0,     'credit': 10},
            {'account_id': self.company_data['default_account_expense'].id,     'debit': 10,    'credit': 0},
        ])
        self.assertRecordValues(invoice02.line_ids, [
            # pylint: disable=bad-whitespace
            {'account_id': self.company_data['default_account_revenue'].id,     'debit': 0,     'credit': 12},
            {'account_id': self.company_data['default_account_receivable'].id,  'debit': 12,    'credit': 0},
        ])

    def test_avco_fully_owned_and_delivered_invoice_post_delivery(self):
        """
        Standard price set to 10. Sale order 2@12. The products are owned by an
        external partner. Invoice after full delivery.
        """
        self.product.categ_id.property_cost_method = 'average'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        self.env['stock.quant']._update_available_quantity(self.product, self.company_data['default_warehouse'].lot_stock_id, 2, owner_id=self.partner_b)

        sale_order = self._so_and_confirm_two_units()
        sale_order.picking_ids.move_line_ids.write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.button_validate()

        invoice = sale_order._create_invoices()
        invoice.action_post()

        # COGS should not exist because the products are owned by an external partner
        amls = invoice.line_ids
        self.assertRecordValues(amls, [
            # pylint: disable=bad-whitespace
            {'account_id': self.company_data['default_account_revenue'].id,     'debit': 0,     'credit': 24},
            {'account_id': self.company_data['default_account_receivable'].id,  'debit': 24,    'credit': 0},
        ])

    # -------------------------------------------------------------------------
    # FIFO Ordered
    # -------------------------------------------------------------------------
    def test_fifo_ordered_invoice_pre_delivery(self):
        """Receive at 8 then at 10. Sale order 2@12. Invoice without delivering.
        As no standard price is set, the Stock OUT and COGS amounts are 0."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'order'

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertAlmostEqual(stock_out_aml.credit, 18)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertAlmostEqual(cogs_aml.debit, 18)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_fifo_ordered_invoice_post_partial_delivery(self):
        """Receive 1@8, 1@10, so 2@12, standard price 12, deliver 1, invoice 2: the COGS amount
        should be 20: 1 really delivered at 10 and the other valued at the standard price 10."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'order'

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # upate the standard price to 12
        self.product.standard_price = 12

        # Invoice 2
        invoice = sale_order._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 2
        invoice_form.save()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_fifo_ordered_invoice_post_delivery(self):
        """Receive at 8 then at 10. Sale order 2@12. Invoice after delivering everything."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'order'

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 18)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 18)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    # -------------------------------------------------------------------------
    # FIFO Delivered
    # -------------------------------------------------------------------------
    def test_fifo_delivered_invoice_pre_delivery(self):
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Invoice the sale order.
        # Nothing delivered = nothing to invoice.
        with self.assertRaises(UserError):
            invoice_id = sale_order._create_invoices()

    def test_fifo_delivered_invoice_post_partial_delivery(self):
        """Receive 1@8, 1@10, so 2@12, standard price 12, deliver 1, invoice 2: the price used should be 10:
        one at 8 and one at 10."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, sale_order.picking_ids.button_validate()).save().process()

        # upate the standard price to 12
        self.product.standard_price = 12

        # Invoice 2
        invoice = sale_order._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 2
        invoice_form.save()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_fifo_delivered_invoice_post_delivery(self):
        """Receive at 8 then at 10. Sale order 2@12. Invoice after delivering everything."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 18)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 18)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

    def test_fifo_delivered_invoice_post_delivery_2(self):
        """Receive at 8 then at 10. Sale order 10@12 and deliver without receiving the 2 missing.
        receive 2@12. Invoice."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        in_move_1 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.write({'quantity': 8, 'picked': True})
        in_move_1._action_done()

        # Create and confirm a sale order for 2@12
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 12,
                    'tax_ids': False,  # no love taxes amls
                })],
        })
        sale_order.action_confirm()

        # Deliver 10
        sale_order.picking_ids.move_ids.write({'quantity': 10, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Make the second receipt
        in_move_2 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.write({'quantity': 2, 'picked': True})
        in_move_2._action_done()
        self.assertEqual(self.product.stock_valuation_layer_ids[-1].value, -4)  # we sent two at 10 but they should have been sent at 12
        self.assertEqual(self.product.stock_valuation_layer_ids[-1].quantity, 0)
        self.assertEqual(sale_order.order_line.move_ids.stock_valuation_layer_ids[-1].quantity, 0)

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 104)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 104)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml.debit, 120)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 120)

    def test_fifo_delivered_invoice_post_delivery_3(self):
        """Receive 5@8, receive 8@12, sale 1@20, deliver, sale 6@20, deliver. Make sure no rouding
        issues appear on the second invoice."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'

        # +5@8
        in_move_1 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 5,
            'price_unit': 8,
        })
        in_move_1._action_confirm()
        in_move_1.write({'quantity': 5, 'picked': True})
        in_move_1._action_done()

        # +8@12
        in_move_2 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.write({'quantity': 8, 'picked': True})
        in_move_2._action_done()

        # sale 1@20, deliver, invoice
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 20,
                    'tax_ids': False,
                })],
        })
        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        sale_order.picking_ids.button_validate()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # sale 6@20, deliver, invoice
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 6,
                    'price_unit': 20,
                    'tax_ids': False,
                })],
        })
        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.write({'quantity': 6, 'picked': True})
        sale_order.picking_ids.button_validate()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # check the last anglo saxon invoice line
        amls = invoice.line_ids
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 56)
        self.assertEqual(cogs_aml.credit, 0)

    def test_fifo_delivered_invoice_post_delivery_4(self):
        """Receive 8@10. Sale order 10@12. Deliver and also invoice it without receiving the 2 missing.
        Now, receive 2@12. Make sure price difference is correctly reflected in expense account."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10

        in_move_1 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.write({'quantity': 8, 'picked': True})
        in_move_1._action_done()

        # Create and confirm a sale order for 10@12
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 12,
                    'tax_ids': False,  # no love taxes amls
                })],
        })
        sale_order.action_confirm()

        # Deliver 10
        sale_order.picking_ids.move_ids.write({'quantity': 10, 'picked': True})
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Make the second receipt
        in_move_2 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.write({'quantity': 2, 'picked': True})
        in_move_2._action_done()

        # check the last anglo saxon move line
        revalued_anglo_expense_amls = sale_order.picking_ids.move_ids.stock_valuation_layer_ids[-1].stock_move_id.account_move_ids[-1].line_ids
        revalued_cogs_aml = revalued_anglo_expense_amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(revalued_cogs_aml.debit, 4, 'Price difference should have correctly reflected in expense account.')

    def test_fifo_delivered_invoice_post_delivery_with_return(self):
        """Receive 2@10. SO1 2@12. Return 1 from SO1. SO2 1@12. Receive 1@20.
        Re-deliver returned from SO1. Invoice after delivering everything."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'

        # Receive 2@10.
        in_move_1 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.write({'quantity': 2, 'picked': True})
        in_move_1._action_done()

        # Create, confirm and deliver a sale order for 2@12 (SO1)
        so_1 = self._so_and_confirm_two_units()
        so_1.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
        so_1.picking_ids.button_validate()

        # Return 1 from SO1
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=so_1.picking_ids.ids, active_id=so_1.picking_ids.ids[0], active_model='stock.picking')
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_ids.write({'quantity': 1, 'picked': True})
        return_pick._action_done()

        # Create, confirm and deliver a sale order for 1@12 (SO2)
        so_2 = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 12,
                    'tax_ids': False,  # no love taxes amls
                })],
        })
        so_2.action_confirm()
        so_2.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        so_2.picking_ids.button_validate()

        # Receive 1@20
        in_move_2 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 20,
        })
        in_move_2._action_confirm()
        in_move_2.write({'quantity': 1, 'picked': True})
        in_move_2._action_done()

        # Re-deliver returned 1 from SO1
        stock_redeliver_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=return_pick.ids, active_id=return_pick.ids[0], active_model='stock.picking')
        )
        stock_redeliver_picking = stock_redeliver_picking_form.save()
        stock_redeliver_picking.product_return_moves.quantity = 1.0
        stock_redeliver_picking_action = stock_redeliver_picking.action_create_returns()
        redeliver_pick = self.env['stock.picking'].browse(stock_redeliver_picking_action['res_id'])
        redeliver_pick.action_assign()
        redeliver_pick.move_ids.write({'quantity': 1, 'picked': True})
        redeliver_pick._action_done()

        # Invoice the sale orders
        invoice_1 = so_1._create_invoices()
        invoice_1.action_post()
        invoice_2 = so_2._create_invoices()
        invoice_2.action_post()

        # Check the resulting accounting entries
        amls_1 = invoice_1.line_ids
        self.assertEqual(len(amls_1), 4)
        stock_out_aml_1 = amls_1.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml_1.debit, 0)
        self.assertEqual(stock_out_aml_1.credit, 30)
        cogs_aml_1 = amls_1.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml_1.debit, 30)
        self.assertEqual(cogs_aml_1.credit, 0)
        receivable_aml_1 = amls_1.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml_1.debit, 24)
        self.assertEqual(receivable_aml_1.credit, 0)
        income_aml_1 = amls_1.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml_1.debit, 0)
        self.assertEqual(income_aml_1.credit, 24)

        amls_2 = invoice_2.line_ids
        self.assertEqual(len(amls_2), 4)
        stock_out_aml_2 = amls_2.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml_2.debit, 0)
        self.assertEqual(stock_out_aml_2.credit, 10)
        cogs_aml_2 = amls_2.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml_2.debit, 10)
        self.assertEqual(cogs_aml_2.credit, 0)
        receivable_aml_2 = amls_2.filtered(lambda aml: aml.account_id == self.company_data['default_account_receivable'])
        self.assertEqual(receivable_aml_2.debit, 12)
        self.assertEqual(receivable_aml_2.credit, 0)
        income_aml_2 = amls_2.filtered(lambda aml: aml.account_id == self.company_data['default_account_revenue'])
        self.assertEqual(income_aml_2.debit, 0)
        self.assertEqual(income_aml_2.credit, 12)

    def test_fifo_uom_computation(self):
        self.env.company.anglo_saxon_accounting = True
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.categ_id.property_valuation = 'real_time'
        quantity = 50.0
        self.product.list_price = 1.5
        self.product.standard_price = 2.0
        unit_12 = self.env['uom.uom'].create({
            'name': 'Pack of 12 units',
            'relative_factor': 12,
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        # Create, confirm and deliver a sale order for 12@1.5 without reception with std_price = 2.0 (SO1)
        so_1 = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'product_uom_id': unit_12.id,
                    'price_unit': 18,
                    'tax_ids': False,  # no love taxes amls
                })],
        })
        so_1.action_confirm()
        so_1.picking_ids.move_ids.write({'quantity': 12, 'picked': True})
        so_1.picking_ids.button_validate()

        # Invoice the sale order.
        invoice_1 = so_1._create_invoices()
        invoice_1.action_post()

        # Invoice 1

        # Correct Journal Items

        # Name                            Debit       Credit

        # Product Sales                    0.00$      18.00$
        # Account Receivable              18.00$       0.00$
        # Default Account Stock Out        0.00$      24.00$
        # Expenses                        24.00$       0.00$

        aml = invoice_1.line_ids
        # Product Sales
        self.assertEqual(aml[0].debit, 0.0)
        self.assertEqual(aml[0].credit, 18.0)
        # Account Receivable
        self.assertEqual(aml[1].debit, 18.0)
        self.assertEqual(aml[1].credit, 0.0)
        # Default Account Stock Out
        self.assertEqual(aml[2].debit, 0.0)
        self.assertEqual(aml[2].credit, 24.0)
        # Expenses
        self.assertEqual(aml[3].debit, 24.0)
        self.assertEqual(aml[3].credit, 0.0)

        # Create stock move 1
        in_move_1 = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': quantity,
            'price_unit': 1.0,
        })
        in_move_1._action_confirm()
        in_move_1.write({'quantity': quantity, 'picked': True})
        in_move_1._action_done()

        # Create, confirm and deliver a sale order for 12@1.5 with reception (50 * 1.0, 50 * 0.0)(SO2)
        so_2 = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'product_uom_id': unit_12.id,
                    'price_unit': 18,
                    'tax_ids': False,  # no love taxes amls
                })],
        })
        so_2.action_confirm()
        so_2.picking_ids.move_ids.write({'quantity': 12, 'picked': True})
        so_2.picking_ids.button_validate()

        # Invoice the sale order.
        invoice_2 = so_2._create_invoices()
        invoice_2.action_post()

        # Invoice 2

        # Correct Journal Items

        # Name                            Debit       Credit

        # Product Sales                    0.00$       18.0$
        # Account Receivable              18.00$        0.0$
        # Default Account Stock Out        0.00$       12.0$
        # Expenses                        12.00$        0.0$

        aml = invoice_2.line_ids
        # Product Sales
        self.assertEqual(aml[0].debit, 0.0)
        self.assertEqual(aml[0].credit, 18.0)
        # Account Receivable
        self.assertEqual(aml[1].debit, 18.0)
        self.assertEqual(aml[1].credit, 0.0)
        # Default Account Stock Out
        self.assertEqual(aml[2].debit, 0.0)
        self.assertEqual(aml[2].credit, 12.0)
        # Expenses
        self.assertEqual(aml[3].debit, 12.0)
        self.assertEqual(aml[3].credit, 0.0)

    def test_fifo_return_and_credit_note(self):
        """
        When posting a credit note for a returned product, the value of the anglo-saxo lines
        should be based on the returned product's value
        """
        self.product.categ_id.property_cost_method = 'fifo'

        # Receive one @10, one @20 and one @60
        in_moves = self.env['stock.move'].create([{
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 20, 60]])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Sell 3 units
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Deliver 1@10, then 1@20 and then 1@60
        pickings = []
        picking = so.picking_ids
        while picking:
            pickings.append(picking)
            picking.move_ids.write({'quantity': 1, 'picked': True})
            action = picking.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
            picking = picking.backorder_ids

        invoice = so._create_invoices()
        invoice.action_post()

        # Receive one @100
        in_moves = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Return the second picking (i.e. 1@20)
        ctx = {'active_id': pickings[1].id, 'active_model': 'stock.picking'}
        return_wizard = Form(self.env['stock.return.picking'].with_context(ctx)).save()
        return_wizard.product_return_moves.quantity = 1
        return_picking = return_wizard._create_return()
        return_picking.move_ids.write({'quantity': 1, 'picked': True})
        return_picking.button_validate()

        # Add a credit note for the returned product
        ctx = {'active_model': 'account.move', 'active_ids': invoice.ids}
        refund_wizard = self.env['account.move.reversal'].with_context(ctx).create({
            'journal_id': invoice.journal_id.id,
        })
        action = refund_wizard.refund_moves()
        reverse_invoice = self.env['account.move'].browse(action['res_id'])
        with Form(reverse_invoice) as reverse_invoice_form:
            with reverse_invoice_form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        reverse_invoice.action_post()

        amls = reverse_invoice.line_ids
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 20, 'Should be to the value of the returned product')
        self.assertEqual(stock_out_aml.credit, 0)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 0)
        self.assertEqual(cogs_aml.credit, 20, 'Should be to the value of the returned product')

    def test_fifo_return_and_create_invoice(self):
        """
        When creating an invoice for a returned product, the value of the anglo-saxo lines
        should be based on the returned product's value
        """
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'

        # Receive one @10, one @20 and one @60
        in_moves = self.env['stock.move'].create([{
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 20, 60]])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Sell 3 units
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Deliver 1@10, then 1@20 and then 1@60
        pickings = []
        picking = so.picking_ids
        while picking:
            pickings.append(picking)
            picking.move_ids.write({'quantity': 1, 'picked': True})
            action = picking.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
            picking = picking.backorder_ids

        invoice = so._create_invoices()
        invoice.action_post()

        # Receive one @100
        in_moves = self.env['stock.move'].create({
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Return the second picking (i.e. 1@20)
        ctx = {'active_id': pickings[1].id, 'active_model': 'stock.picking'}
        return_wizard = Form(self.env['stock.return.picking'].with_context(ctx)).save()
        return_wizard.product_return_moves.quantity = 1
        return_picking = return_wizard._create_return()
        return_picking.move_ids.write({'quantity': 1, 'picked': True})
        return_picking.button_validate()

        # Create a new invoice for the returned product
        self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': so.ids,
        }).sudo().create({}).create_invoices()
        reverse_invoice = so.invoice_ids[-1]
        with Form(reverse_invoice) as reverse_invoice_form:
            with reverse_invoice_form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        reverse_invoice.action_post()

        amls = reverse_invoice.line_ids
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 20, 'Should be to the value of the returned product')
        self.assertEqual(stock_out_aml.credit, 0)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 0)
        self.assertEqual(cogs_aml.credit, 20, 'Should be to the value of the returned product')

    def test_fifo_several_invoices_reset_repost(self):
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'

        svl_values = [10, 15, 65]
        total_value = sum(svl_values)
        in_moves = self.env['stock.move'].create([{
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in svl_values])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Deliver one by one, so it creates an out-SVL each time.
        # Then invoice the delivered quantity
        invoices = self.env['account.move']
        picking = so.picking_ids
        while picking:
            picking.move_ids.write({'quantity': 1, 'picked': True})
            action = picking.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
            picking = picking.backorder_ids

            invoice = so._create_invoices()
            invoice.action_post()
            invoices |= invoice

        out_account = self.product.categ_id.property_stock_account_output_categ_id
        invoice01, _invoice02, invoice03 = invoices
        cogs = invoices.line_ids.filtered(lambda l: l.account_id == out_account)
        self.assertEqual(cogs.mapped('credit'), svl_values)

        # Reset and repost each invoice
        for i, inv in enumerate(invoices):
            inv.button_draft()
            inv.action_post()
            cogs = invoices.line_ids.filtered(lambda l: l.account_id == out_account)
            self.assertEqual(cogs.mapped('credit'), svl_values, 'Incorrect values while posting again invoice %s' % (i + 1))

        # Reset and repost all invoices (we only check the total value as the
        # distribution changes but does not really matter)
        invoices.button_draft()
        invoices.action_post()
        cogs = invoices.line_ids.filtered(lambda l: l.account_id == out_account)
        self.assertEqual(sum(cogs.mapped('credit')), total_value)

        # Reset and repost few invoices (we only check the total value as the
        # distribution changes but does not really matter)
        (invoice01 | invoice03).button_draft()
        (invoice01 | invoice03).action_post()
        cogs = invoices.line_ids.filtered(lambda l: l.account_id == out_account)
        self.assertEqual(sum(cogs.mapped('credit')), total_value)

    def test_fifo_reverse_and_create_new_invoice(self):
        """
        FIFO automated
        Receive 1@10, 1@50
        Deliver 1
        Post the invoice, add a credit note with option 'new draft inv'
        Post the second invoice
        COGS should be based on the delivered product

        Note: This test will also ensure that a user who only has access to
        account app can post such an invoice
        """
        self.product.categ_id.property_cost_method = 'fifo'

        accountman = self.env['res.users'].create({
            'name': 'Super Accountman',
            'login': 'super_accountman',
            'password': 'super_accountman',
            'group_ids': [(6, 0, self.env.ref('account.group_account_invoice').ids)],
        })

        in_moves = self.env['stock.move'].create([{
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 50]])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        picking = so.picking_ids
        picking.move_ids.write({'quantity': 1.0, 'picked': True})
        picking.button_validate()

        invoice01 = so._create_invoices()

        # Clear the cache to ensure access rights
        self.env.invalidate_all()
        invoice01.with_user(accountman.id).action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice01.ids).create({
            'journal_id': invoice01.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        invoice02 = self.env['account.move'].browse(reversal['res_id'])
        invoice02.action_post()

        amls = invoice02.line_ids
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)

    def test_fifo_edit_svl_without_reinvoice(self):
        """Edit SVL move line after delivering. Check no reinvoicing occurs."""
        self.product.categ_id.property_cost_method = 'fifo'
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10
        self.product.expense_policy = 'cost'

        self._fifo_in_one_eight_one_ten()

        # Create and confirm a sale order for 2@12
        sale_order = self._so_and_confirm_two_units()
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.product_uom_qty, 2.0)

        # Deliver one.
        sale_order.picking_ids.move_ids.write({'quantity': 2, 'picked': True})
        sale_order.picking_ids.button_validate()
        svl_am = sale_order.order_line.move_ids.stock_valuation_layer_ids.account_move_id
        svl_am.button_draft()
        svl_am.action_post()

        # Check no reinvoice line addded to the sale order
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.product_uom_qty, 2.0)

    def test_anglo_saxon_cogs_with_down_payment(self):
        """Create a SO with a product invoiced on delivered quantity.
        Do a 100% down payment, deliver a part of it with a backorder
        then invoice the delivered part from the down payment.
        Deliver the remaining part and invoice it."""
        self.product.invoice_policy = 'delivery'
        self.product.standard_price = 10
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,  # tracking serial
            'inventory_quantity': 20,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        }).action_apply_inventory()

        # Create a SO with a product invoiced on delivered quantity
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Do a 100% down payment
        self.env['sale.advance.payment.inv'].sudo().create({
            'advance_payment_method': 'percentage',
            'amount': 100,
            'sale_order_ids': so.ids,
        }).create_invoices()

        # Invoice the delivered part from the down payment
        down_payment_invoices = so.invoice_ids
        down_payment_invoices.action_post()

        # Deliver a part of it with a backorder
        so.picking_ids.move_ids.quantity = 4
        so.picking_ids.move_ids.picked = True
        Form.from_action(self.env, so.picking_ids.button_validate()).save().process()

        self.env['sale.advance.payment.inv'].with_context(
            active_ids=so.ids,
        ).sudo().create({}).create_invoices()
        credit_note = so.invoice_ids.filtered(lambda i: i.state != 'posted')
        self.assertEqual(len(credit_note), 1)
        self.assertEqual(len(credit_note.invoice_line_ids.filtered(lambda line: line.display_type == 'product')), 2)
        down_payment_line = credit_note.invoice_line_ids.filtered(lambda line: line.sale_line_ids.is_downpayment)
        down_payment_line.quantity = 0.4
        credit_note.action_post()
        # Deliver the remaining part and invoice itµ
        backorder = so.picking_ids.filtered(lambda p: p.state != 'done')
        backorder.move_ids.quantity = 6
        backorder.move_ids.picked = True
        backorder.button_validate()

        self.env['sale.advance.payment.inv'].with_context(
            active_ids=so.ids,
        ).sudo().create({}).create_invoices()

        invoice = so.invoice_ids.filtered(lambda i: i.state != 'posted')
        invoice.action_post()

        # Check the resulting accounting entries
        account_stock_out = self.company_data['default_account_stock_out']
        account_expense = self.company_data['default_account_expense']
        invoice_1_cogs = credit_note.line_ids.filtered(lambda l: l.display_type == 'cogs')
        invoice_2_cogs = invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')
        self.assertRecordValues(invoice_1_cogs, [
            {'debit': 0, 'credit': 40, 'account_id': account_stock_out.id, 'reconciled': True},
            {'debit': 40, 'credit': 0, 'account_id': account_expense.id, 'reconciled': False},
        ])
        self.assertRecordValues(invoice_2_cogs, [
            {'debit': 0, 'credit': 60, 'account_id': account_stock_out.id, 'reconciled': True},
            {'debit': 60, 'credit': 0, 'account_id': account_expense.id, 'reconciled': False},
        ])

    def test_anglo_saxon_cogs_validate_invoice(self):
        """ Having some FIFO + real-time valued product with an established price i.e., from an in
        move: generating a delivery via sale, processing that delivery in multiple parts, and
        invoicing the sale in multiple parts should not cause the valuation mechanism to "run out"
        of product quantity during consumption of the stock valuation layers which were generated
        by the out moves.

        In that scenario, if there have been any manual changes to a product's `standard_price`,
        there will be inaccurate product expense account (COGs) lines on the affected invoice.
        """
        product = self.product
        in_move = self.env['stock.move'].create({
            'product_id': product.id,
            'price_unit': 100,
            'product_uom_qty': 12,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
        })
        in_move._action_confirm()
        in_move._action_assign()
        in_move.move_line_ids.quantity = 12
        in_move.picked = True
        in_move._action_done()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 10,
                'price_unit': 100,
            }), Command.create({
                'product_id': product.id,
                'product_uom_qty': 2,
                'price_unit': 100,
            })],
        })
        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        delivery.move_ids.filtered(lambda m: m.product_uom_qty == 2).quantity = 0
        r = delivery.button_validate()
        Form(self.env[r['res_model']].with_context(r['context'])).save().process()
        backorder_delivery = sale_order.picking_ids.filtered(lambda p: p.state != 'done')
        backorder_delivery.move_ids.quantity = 2
        backorder_delivery.button_validate()
        self.env['sale.advance.payment.inv'].with_context(
            active_ids=sale_order.ids,
        ).sudo().create({}).create_invoices()

        invoice = sale_order.invoice_ids
        qty_ten_invoice_line = invoice.invoice_line_ids.filtered(lambda l: l.quantity == 10)
        qty_ten_invoice_line.quantity = 5
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        product.standard_price = 50
        self.env['sale.advance.payment.inv'].with_context(
            active_ids=sale_order.ids,
        ).sudo().create({}).create_invoices()
        invoice2 = sale_order.invoice_ids.filtered(lambda i: i.state != 'posted')
        invoice2.invoice_date = fields.Date.today()
        invoice2.action_post()
        invoice2_cogs_lines = invoice2.line_ids.filtered(lambda l: l.display_type == 'cogs')
        self.assertRecordValues(
            invoice2_cogs_lines,
            [
                {'credit': 500, 'debit': 0},
                {'credit': 0, 'debit': 500},
            ]
        )
