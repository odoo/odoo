# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import SavepointCase
from odoo.exceptions import UserError


class TestAngloSaxonValuation(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestAngloSaxonValuation, cls).setUpClass()
        cls.env.user.company_id.anglo_saxon_accounting = True
        cls.product = cls.env['product.product'].create({
            'name': 'product',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.stock_input_account = cls.env['account.account'].create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.stock_output_account = cls.env['account.account'].create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.stock_valuation_account = cls.env['account.account'].create({
            'name': 'Stock Valuation',
            'code': 'StockVal',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
        })
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Expense Account',
            'code': 'Exp',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
        })
        cls.income_account = cls.env['account.account'].create({
            'name': 'Income Account',
            'code': 'Inc',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
        })
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        cls.product.write({
            'property_account_expense_id': cls.expense_account.id,
            'property_account_income_id': cls.income_account.id,
        })
        cls.product.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
            'property_valuation': 'real_time',
        })
        cls.stock_location = cls.env['stock.warehouse'].search([], limit=1).lot_stock_id
        cls.recv_account = cls.env['account.account'].create({
            'name': 'account receivable',
            'code': 'RECV',
            'user_type_id': cls.env.ref('account.data_account_type_receivable').id,
            'reconcile': True,
        })
        cls.pay_account = cls.env['account.account'].create({
            'name': 'account payable',
            'code': 'PAY',
            'user_type_id': cls.env.ref('account.data_account_type_payable').id,
            'reconcile': True,
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'customer',
            'property_account_receivable_id': cls.recv_account.id,
            'property_account_payable_id': cls.pay_account.id,
        })
        cls.journal_sale = cls.env['account.journal'].create({
            'name': 'Sale Journal - Test',
            'code': 'AJ-SALE',
            'type': 'sale',
            'company_id': cls.env.user.company_id.id,
        })
        cls.counterpart_account = cls.env['account.account'].create({
            'name': 'Counterpart account',
            'code': 'Count',
            'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
        })

    def _inv_adj_two_units(self):
        inventory = self.env['stock.inventory'].create({
            'name': 'test',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product.id)],
        })
        inventory.action_start()
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'location_id': self.stock_location.id,
            'product_id': self.product.id,
            'product_qty': 2,
        })
        inventory.action_validate()

    def _so_and_confirm_two_units(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
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
            'location_dest_id': self.stock_location.id,
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
            'location_dest_id': self.stock_location.id,
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
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 28)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 28)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # Invoice 1
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 1
        invoice_form.save()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids[0].move_lines.quantity_done = 1
        sale_order.picking_ids[0].button_validate()

        # change the standard price to 16
        self.product.standard_price = 16.0

        # invoice 1
        invoice2 = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice2.post()
        amls = invoice2.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 14)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 14)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids.filtered('backorder_id').move_lines.quantity_done = 1
        sale_order.picking_ids.filtered('backorder_id').button_validate()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 24)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 24)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # Invoice 1
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 1
        invoice_form.save()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 12)

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids[0].move_lines.quantity_done = 1
        sale_order.picking_ids[0].button_validate()

        # change the standard price to 16
        self.product.standard_price = 16.0

        # invoice 1
        invoice2 = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice2.post()
        amls = invoice2.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 14)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 14)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # change the standard price to 14
        self.product.standard_price = 14.0

        # deliver the backorder
        sale_order.picking_ids.filtered('backorder_id').move_lines.quantity_done = 1
        sale_order.picking_ids.filtered('backorder_id').button_validate()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 24)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 24)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 2
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 10)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 10)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 12)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 2
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
        self.assertEqual(income_aml.debit, 0)
        self.assertEqual(income_aml.credit, 24)

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
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertAlmostEqual(stock_out_aml.credit, 16)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertAlmostEqual(cogs_aml.debit, 16)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # upate the standard price to 12
        self.product.standard_price = 12

        # Invoice 2
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 2
        invoice_form.save()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 2
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 18)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 18)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        wiz = sale_order.picking_ids.button_validate()
        wiz = Form(self.env[wiz['res_model']].with_context(wiz['context'])).save()
        wiz.process()

        # upate the standard price to 12
        self.product.standard_price = 12

        # Invoice 2
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice_form = Form(invoice)
        with invoice_form.invoice_line_ids.edit(0) as invoice_line:
            invoice_line.quantity = 2
        invoice_form.save()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 20)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 20)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
        sale_order.picking_ids.move_lines.quantity_done = 2
        sale_order.picking_ids.button_validate()

        # Invoice the sale order.
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 18)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 18)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 24)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
            'location_dest_id': self.stock_location.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 10,
        })
        in_move_1._action_confirm()
        in_move_1.quantity_done = 8
        in_move_1._action_done()

        # Create and confirm a sale order for 2@12
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
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
        sale_order.picking_ids.move_lines.quantity_done = 10
        sale_order.picking_ids.button_validate()

        # Make the second receipt
        in_move_2 = self.env['stock.move'].create({
            'name': 'a',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.stock_location.id,
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
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.stock_output_account)
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertEqual(stock_out_aml.credit, 104)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 104)
        self.assertEqual(cogs_aml.credit, 0)
        receivable_aml = amls.filtered(lambda aml: aml.account_id == self.recv_account)
        self.assertEqual(receivable_aml.debit, 120)
        self.assertEqual(receivable_aml.credit, 0)
        income_aml = amls.filtered(lambda aml: aml.account_id == self.income_account)
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
            'location_dest_id': self.stock_location.id,
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
            'location_dest_id': self.stock_location.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 8,
            'price_unit': 12,
        })
        in_move_2._action_confirm()
        in_move_2.quantity_done = 8
        in_move_2._action_done()

        # sale 1@20, deliver, invoice
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
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
        sale_order.picking_ids.move_lines.quantity_done = 1
        sale_order.picking_ids.button_validate()
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # sale 6@20, deliver, invoice
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
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
        sale_order.picking_ids.move_lines.quantity_done = 6
        sale_order.picking_ids.button_validate()
        invoice = sale_order.with_context(default_journal_id=self.journal_sale.id)._create_invoices()
        invoice.post()

        # check the last anglo saxon invoice line
        amls = invoice.line_ids
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.expense_account)
        self.assertEqual(cogs_aml.debit, 56)
        self.assertEqual(cogs_aml.credit, 0)
