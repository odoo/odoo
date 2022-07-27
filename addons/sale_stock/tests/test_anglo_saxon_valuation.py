# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAngloSaxonValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.company_id.anglo_saxon_accounting = True

        cls.product = cls.env['product.product'].create({
            'name': 'product',
            'type': 'product',
            'categ_id': cls.stock_account_product_categ.id,
        })

    def _inv_adj_two_units(self):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,  # tracking serial
            'inventory_quantity': 2,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
        }).action_apply_inventory()

    def _so_and_confirm_two_units(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 2.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                    'tax_id': False,  # no love taxes amls
                })],
        })
        sale_order.action_confirm()
        return sale_order

    def _fifo_in_one_eight_one_ten(self):
        # Put two items in stock.
        in_move_1 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 8,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = 1
        in_move_1._action_done()
        in_move_2 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 10,
        })
        in_move_2._action_confirm()
        in_move_2.quantity_done = 1
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

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
        sale_order.picking_ids[0].move_ids.quantity_done = 1
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids.filtered('backorder_id').move_ids.quantity_done = 1
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

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
        sale_order.picking_ids[0].move_ids.quantity_done = 1
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids.filtered('backorder_id').move_ids.quantity_done = 1
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

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
        sale_order.picking_ids.move_ids.quantity_done = 2
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
        product.type = 'product'
        product.categ_id.property_cost_method = 'average'
        product.categ_id.property_valuation = 'real_time'
        product.list_price = 100
        product.standard_price = 50

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 5.0,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
        })
        so.action_confirm()

        pick = so.picking_ids
        pick.move_ids.write({'quantity_done': 5})
        pick.button_validate()

        product.standard_price = 40

        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=pick.ids, active_id=pick.sorted().ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 1
        return_wiz.product_return_moves.to_refund = False
        res = return_wiz.create_returns()

        return_pick = self.env['stock.picking'].browse(res['res_id'])
        return_pick.move_ids.write({'quantity_done': 1})
        return_pick.button_validate()

        picking = self.env['stock.picking'].create({
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'picking_type_id': self.company_data['default_warehouse'].in_type_id.id,
        })
        # We don't set the price_unit so that the `standard_price` will be used (see _get_price_unit()):
        self.env['stock.move'].create({
            'name': 'test_immediate_validate_1',
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'picking_id': picking.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'quantity_done': 1,
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

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
        sale_order.picking_ids.move_ids.quantity_done = 2
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
        sale_order.picking_ids.move_line_ids.qty_done = 1
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
            {'account_id': self.company_data['default_account_stock_out'].id,   'debit': 0,     'credit': 0},
            {'account_id': self.company_data['default_account_expense'].id,     'debit': 0,     'credit': 0},
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
        sale_order.picking_ids.move_line_ids.qty_done = 2
        sale_order.picking_ids.button_validate()

        invoice = sale_order._create_invoices()
        invoice.action_post()

        # COGS should not exist because the products are owned by an external partner
        amls = invoice.line_ids
        self.assertRecordValues(amls, [
            # pylint: disable=bad-whitespace
            {'account_id': self.company_data['default_account_revenue'].id,     'debit': 0,     'credit': 24},
            {'account_id': self.company_data['default_account_receivable'].id,  'debit': 24,    'credit': 0},
            {'account_id': self.company_data['default_account_stock_out'].id,   'debit': 0,     'credit': 0},
            {'account_id': self.company_data['default_account_expense'].id,     'debit': 0,     'credit': 0},
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
        self.assertAlmostEqual(stock_out_aml.credit, 16)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertAlmostEqual(cogs_aml.debit, 16)
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

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
        sale_order.picking_ids.move_ids.quantity_done = 2
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
        sale_order.picking_ids.move_ids.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

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
        sale_order.picking_ids.move_ids.quantity_done = 2
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
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = 8
        in_move_1._action_done()

        # Create and confirm a sale order for 2@12
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 10.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                    'tax_id': False,  # no love taxes amls
                })],
        })
        sale_order.action_confirm()

        # Deliver 10
        sale_order.picking_ids.move_ids.quantity_done = 10
        sale_order.picking_ids.button_validate()

        # Make the second receipt
        in_move_2 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.quantity_done = 2
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
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 5,
            'price_unit': 8,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = 5
        in_move_1._action_done()

        # +8@12
        in_move_2 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.quantity_done = 8
        in_move_2._action_done()

        # sale 1@20, deliver, invoice
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 20,
                    'tax_id': False,
                })],
        })
        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.quantity_done = 1
        sale_order.picking_ids.button_validate()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # sale 6@20, deliver, invoice
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 6,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 20,
                    'tax_id': False,
                })],
        })
        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.quantity_done = 6
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
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = 8
        in_move_1._action_done()

        # Create and confirm a sale order for 10@12
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 10.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                    'tax_id': False,  # no love taxes amls
                })],
        })
        sale_order.action_confirm()

        # Deliver 10
        sale_order.picking_ids.move_ids.quantity_done = 10
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Make the second receipt
        in_move_2 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.quantity_done = 2
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
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 2,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = 2
        in_move_1._action_done()

        # Create, confirm and deliver a sale order for 2@12 (SO1)
        so_1 = self._so_and_confirm_two_units()
        so_1.picking_ids.move_ids.quantity_done = 2
        so_1.picking_ids.button_validate()

        # Return 1 from SO1
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=so_1.picking_ids.ids, active_id=so_1.picking_ids.ids[0], active_model='stock.picking')
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_ids.quantity_done = 1
        return_pick._action_done()

        # Create, confirm and deliver a sale order for 1@12 (SO2)
        so_2 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 12,
                    'tax_id': False,  # no love taxes amls
                })],
        })
        so_2.action_confirm()
        so_2.picking_ids.move_ids.quantity_done = 1
        so_2.picking_ids.button_validate()

        # Receive 1@20
        in_move_2 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 20,
        })
        in_move_2._action_confirm()
        in_move_2.quantity_done = 1
        in_move_2._action_done()

        # Re-deliver returned 1 from SO1
        stock_redeliver_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=return_pick.ids, active_id=return_pick.ids[0], active_model='stock.picking')
        )
        stock_redeliver_picking = stock_redeliver_picking_form.save()
        stock_redeliver_picking.product_return_moves.quantity = 1.0
        stock_redeliver_picking_action = stock_redeliver_picking.create_returns()
        redeliver_pick = self.env['stock.picking'].browse(stock_redeliver_picking_action['res_id'])
        redeliver_pick.action_assign()
        redeliver_pick.move_ids.quantity_done = 1
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
            'category_id': self.product.uom_id.category_id.id,
            'uom_type': 'bigger',
            'factor_inv': 12,
            'rounding': 1,
        })

        # Create, confirm and deliver a sale order for 12@1.5 without reception with std_price = 2.0 (SO1)
        so_1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'product_uom': unit_12.id,
                    'price_unit': 18,
                    'tax_id': False,  # no love taxes amls
                })],
        })
        so_1.action_confirm()
        so_1.picking_ids.move_ids.quantity_done = 12
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
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': quantity,
            'price_unit': 1.0,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = quantity
        in_move_1._action_done()

        # Create, confirm and deliver a sale order for 12@1.5 with reception (50 * 1.0, 50 * 0.0)(SO2)
        so_2 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'product_uom': unit_12.id,
                    'price_unit': 18,
                    'tax_id': False,  # no love taxes amls
                })],
        })
        so_2.action_confirm()
        so_2.picking_ids.move_ids.quantity_done = 12
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
            'name': 'IN move @%s' % p,
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 20, 60]])
        in_moves._action_confirm()
        in_moves.quantity_done = 1
        in_moves._action_done()

        # Sell 3 units
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 3.0,
                    'product_uom': self.product.uom_id.id,
                    'price_unit': 100,
                    'tax_id': False,
                })],
        })
        so.action_confirm()

        # Deliver 1@10, then 1@20 and then 1@60
        pickings = []
        picking = so.picking_ids
        while picking:
            pickings.append(picking)
            picking.move_ids.quantity_done = 1
            action = picking.button_validate()
            if isinstance(action, dict):
                wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
                wizard.process()
            picking = picking.backorder_ids

        invoice = so._create_invoices()
        invoice.action_post()

        # Receive one @100
        in_moves = self.env['stock.move'].create({
            'name': 'IN move @100',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        in_moves._action_confirm()
        in_moves.quantity_done = 1
        in_moves._action_done()

        # Return the second picking (i.e. 1@20)
        ctx = {'active_id': pickings[1].id, 'active_model': 'stock.picking'}
        return_wizard = Form(self.env['stock.return.picking'].with_context(ctx)).save()
        return_picking_id, dummy = return_wizard._create_returns()
        return_picking = self.env['stock.picking'].browse(return_picking_id)
        return_picking.move_ids.quantity_done = 1
        return_picking.button_validate()

        # Add a credit note for the returned product
        ctx = {'active_model': 'account.move', 'active_ids': invoice.ids}
        refund_wizard = self.env['account.move.reversal'].with_context(ctx).create({
            'refund_method': 'refund',
            'journal_id': invoice.journal_id.id,
        })
        action = refund_wizard.reverse_moves()
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
