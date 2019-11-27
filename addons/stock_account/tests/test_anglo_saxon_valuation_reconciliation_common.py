# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.stock_account.tests.common import StockAccountTestCommon
from odoo import fields

class ValuationReconciliationTestCommon(StockAccountTestCommon):
    """ Base class for tests checking interim accounts reconciliation works
    in anglosaxon accounting. It sets up everything we need in the tests, and is
    extended in both sale_stock and purchase modules to run the 'true' tests.
    """

    def check_reconciliation(self, invoice, picking, full_reconcile=True, operation='purchase'):
        interim_account_id = operation == 'purchase' and self.input_account.id or self.output_account.id
        invoice_line = invoice.line_ids.filtered(lambda line: line.account_id.id == interim_account_id)

        stock_moves = picking.move_lines

        valuation_line = stock_moves.mapped('account_move_ids.line_ids').filtered(lambda x: x.account_id.id == interim_account_id)

        if invoice.is_purchase_document() and any(l.is_anglo_saxon_line for l in invoice_line):
            self.assertEqual(len(invoice_line), 2, "Only two line2 should have been written by invoice in stock input account")
            self.assertTrue(valuation_line.reconciled or invoice_line[0].reconciled or invoice_line[1].reconciled, "The valuation and invoice line should have been reconciled together.")
        else:
            self.assertEqual(len(invoice_line), 1, "Only one line should have been written by invoice in stock input account")
            self.assertTrue(valuation_line.reconciled or invoice_line.reconciled, "The valuation and invoice line should have been reconciled together.")

        if invoice.type not in ('out_refund', 'in_refund'):
            self.assertEqual(len(valuation_line), 1, "Only one line should have been written for stock valuation in stock input account")

            if full_reconcile:
                self.assertTrue(valuation_line.full_reconcile_id, "The reconciliation should be total at that point.")
            else:
                self.assertFalse(valuation_line.full_reconcile_id, "The reconciliation should not be total at that point.")

    def _process_pickings(self, pickings, date=False, quantity=False):
        if not date:
            date = fields.Date.today()
        pickings.action_confirm()
        pickings.action_assign()
        for picking in pickings:
            for ml in picking.move_line_ids:
                ml.qty_done = quantity or ml.product_qty
        pickings._action_done()
        self._change_pickings_date(pickings, date)

    def _change_pickings_date(self, pickings, date):
        pickings.mapped('move_lines').write({'date': date})
        pickings.mapped('move_lines.account_move_ids').write({'name': '/', 'state': 'draft'})
        pickings.mapped('move_lines.account_move_ids').write({'date': date})
        pickings.move_lines.account_move_ids.post()

    def _create_product_category(self):
        return self.env['product.category'].create({
            'name': 'Test category',
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
            'property_stock_valuation_account_id': self.valuation_account.id,
            'property_stock_account_input_categ_id': self.input_account.id,
            'property_stock_account_output_categ_id': self.output_account.id,
        })

    def setUp(self):
        super(ValuationReconciliationTestCommon, self).setUp()

        self.company = self.env.company
        self.company.anglo_saxon_accounting = True
        self.currency_one = self.company.currency_id
        currency_two_name = 'USD' if self.currency_one.name != 'USD' else 'EUR'
        self.currency_two = self.env['res.currency'].search([('name', '=', currency_two_name)])

        self.input_account = self.env['account.account'].create({
            'name': 'Test stock in',
            'code': 'stock_account_TEST_42',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
            'company_id': self.company.id,
        })

        self.output_account = self.env['account.account'].create({
            'name': 'Test stock out',
            'code': 'stock_account_TEST_43',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
            'company_id': self.company.id,
        })

        self.valuation_account = self.env['account.account'].create({
            'name': 'Test stock valuation',
            'code': 'stock_account_TEST_44',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
            'company_id': self.company.id,
        })


        self.test_product_category = self._create_product_category()

        uom = self.env['uom.uom'].search([], limit=1)
        test_product_delivery_inv_template = self.env['product.template'].create({
            'name': 'Test product template invoiced on delivery',
            'type': 'product',
            'categ_id': self.test_product_category.id,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
        })
        test_product_order_inv_template = self.env['product.template'].create({
            'name': 'Test product template invoiced on order',
            'type': 'product',
            'categ_id': self.test_product_category.id,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
        })

        self.test_product_order = test_product_order_inv_template.product_variant_id
        self.test_product_order.write({
            'name': 'The chocolate moose - order',
            'standard_price': 42.0,
        })

        self.test_product_delivery = test_product_delivery_inv_template.product_variant_id
        self.test_product_delivery.write({
            'name': 'The chocolate moose - delivery',
            'standard_price': 42.0,
        })

        self.test_partner = self.env['res.partner'].create({
            'name': 'Ruben Rybnik',
        })

        self.product_price_unit = 66.0

        # We delete the currency rate defined in demo data for USD on June 6th.
        # This is mandatory to ensure consistency of the data generated by the test,
        # as stock pickings created from a PO are by design always created for
        # the current date (there is no way forcing this), meaning that they
        # always use today's exchange rate for their valuation.
        # Despite the fact we rewrite the date of the valuation moves artificially,
        # we cannot correct the debit and credit values, since the anglosaxon
        # entries get automatically reconciled (and you cannot modify a reconciled entry).
        # So, we have to make sure that "today"'s rate will always be the last rate we
        # created in order to ensure complete control of the test.
        rateUSDbis = self.env.ref('base.rateUSDbis', raise_if_not_found=False)
        if rateUSDbis:
            rateUSDbis.unlink()
