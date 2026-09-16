# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo import fields, Command


@tagged("post_install", "-at_install")
class TestAccountMove(TestStockValuationCommon):
    def test_standard_perpetual_01_mc_01(self):
        product = self.product_standard_auto
        self._use_multi_currencies([('2017-01-01', 2.0)])
        rate = self.other_currency.rate_ids.rate

        invoice = self._create_invoice(
            product=product, price_unit=40, post=False, currency_id=self.other_currency.id
        )

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertEqual(len(invoice.line_ids), 2)
        self.assertEqual(len(invoice.line_ids.currency_id), 1)

        invoice._post()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.line_ids), 4)
        self.assertEqual(len(invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')), 2)
        self.assertEqual(len(invoice.line_ids.currency_id), 2)

    def test_fifo_perpetual_01_mc_01(self):
        product = self.product_fifo_auto
        self._use_multi_currencies([('2017-01-01', 2.0)])
        rate = self.other_currency.rate_ids.rate

        invoice = self._create_invoice(
            product=product, price_unit=40, post=False, currency_id=self.other_currency.id
        )

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertEqual(len(invoice.line_ids), 2)
        self.assertEqual(len(invoice.line_ids.currency_id), 1)

        invoice._post()
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.line_ids), 4)
        self.assertEqual(len(invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')), 2)
        self.assertEqual(len(invoice.line_ids.currency_id), 2)

    def test_average_perpetual_01_mc_01(self):
        product = self.product_avco_auto
        self._use_multi_currencies([('2017-01-01', 2.0)])
        rate = self.other_currency.rate_ids.rate

        invoice = self._create_invoice(
            product=product, price_unit=40, post=False, currency_id=self.other_currency.id
        )

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertEqual(len(invoice.line_ids), 2)
        self.assertEqual(len(invoice.line_ids.currency_id), 1)

        invoice._post()

        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_total)
        self.assertAlmostEqual(product.lst_price * rate, invoice.amount_residual)
        self.assertEqual(len(invoice.line_ids), 4)
        self.assertEqual(len(invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')), 2)
        self.assertEqual(len(invoice.line_ids.currency_id), 2)

    def test_storno_accounting(self):
        """Storno accounting uses negative numbers on debit/credit to cancel other moves.
        This test checks that we do the same for the anglosaxon lines when storno is enabled.
        """
        self._use_multi_currencies([('2017-01-01', 2.0)])

        product = self.product_standard_auto
        self.env.company.account_storno = True
        self.env.company.anglo_saxon_accounting = True

        self._create_credit_note(
            product=product, currency_id=self.other_currency.id, invoice_date=fields.Date.from_string('2019-01-01')
        )

        stock_output_line = self._get_stock_valuation_move_lines()
        self.assertEqual(stock_output_line.debit, 0)
        self.assertEqual(stock_output_line.credit, -10)

        expense_line = self._get_expense_move_lines()
        self.assertEqual(expense_line.debit, -10)
        self.assertEqual(expense_line.credit, 0)

    def test_standard_manual_tax_edit(self):
        ''' Test manually editing tax amount, cogs creation should not reset tax amount '''
        product = self.product_standard_auto

        invoice = self._create_invoice(
            product=product, price_unit=100, post=False, tax_ids=[Command.set(self.env.company.account_sale_tax_id.ids)]
        )

        self.assertEqual(invoice.amount_total, 115)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 15)

        # simulate manual tax edit via widget
        tax_totals = invoice.tax_totals
        tax_totals['subtotals'][0]['tax_groups'][0]['tax_amount_currency'] = 14.0
        invoice.tax_totals = tax_totals

        self.assertEqual(len(invoice.line_ids), 3)
        self.assertEqual(invoice.amount_total, 114)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 14)

        invoice._post()

        self.assertEqual(len(invoice.line_ids), 5)
        self.assertEqual(invoice.amount_total, 114)
        self.assertEqual(invoice.amount_untaxed, 100)
        self.assertEqual(invoice.amount_tax, 14)

    def test_basic_bill(self):
        """
        When billing a storable product with a basic category (manual
        valuation), the account used should be the expenses one. This test
        checks the flow with two companies:
        - One that existed before the installation of `stock_account` (to test
        the post-install hook)
        - One created after the module installation
        """
        self.env.user.company_ids |= self.other_company

        for company in (self.company | self.other_company):
            bill = self._create_bill(
                product=self.product_standard, price_unit=100, partner_id=self.partner.id, company_id=company.id
            )

            product_accounts = self.product_standard.product_tmpl_id.with_company(company.id).get_product_accounts()
            self.assertEqual(bill.invoice_line_ids.account_id, product_accounts['expense'])

    def test_cogs_analytic_accounting(self):
        """Check analytic distribution is correctly propagated to COGS lines.
        Both the debit interim account line and the credit expense account line
        should carry the analytic distribution; otherwise analytic accounting
        becomes unbalanced."""
        product = self.product_standard_auto
        default_plan = self.env['account.analytic.plan'].create({
            'name': 'Default',
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Account 1',
            'plan_id': default_plan.id,
            'company_id': False,
        })

        move = self._create_credit_note(
            product=product, invoice_date=fields.Date.from_string('2019-01-01'), analytic_distribution={analytic_account.id: 100}
        )

        cogs_lines = move.line_ids.filtered(lambda l: l.display_type == 'cogs')
        self.assertRecordValues(cogs_lines.sorted('balance'), [
            {'analytic_distribution': {str(analytic_account.id): 100}, 'account_id': product._get_product_accounts()['expense'].id},
            {'analytic_distribution': {str(analytic_account.id): 100}, 'account_id': product._get_product_accounts()['stock_valuation'].id},
        ])

    def test_stock_picking_applies_analytic_distribution_to_journal_entry(self):
        """
        Check analytic distribution is correctly propagated to journal entry
        while validating a picking related to a partner
        """
        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')
        product = self.product_standard_auto
        cost_of_production = self._use_inventory_location_accounting()
        default_plan = self.env['account.analytic.plan'].create({
            'name': 'Default',
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Account 1',
            'plan_id': default_plan.id,
            'company_id': False,
        })
        self.env['account.analytic.distribution.model'].create({
            'analytic_distribution': {analytic_account.id: 100},
            'product_id': product.id,
            'company_id': self.company.id,
            'partner_id': self.partner.id,
        })
        self.stock_location.valuation_account_id = cost_of_production.id

        self._make_in_move(
            product=product, quantity=1, create_picking=True, company=self.company, partner_id=self.partner.id
        )

        aml = self.env['account.move.line'].search([('product_id', '=', product.id)], order='debit')
        self.assertRecordValues(aml, [
            {'analytic_distribution': {str(analytic_account.id): 100}, 'credit': 10, 'debit': 0},
            {'analytic_distribution': {str(analytic_account.id): 100}, 'credit': 0, 'debit': 10},
        ])

    def test_cogs_account_branch_company(self):
        """Check branch company accounts are selected"""
        product = self.product_standard_auto
        branch = self.branch
        test_account = self.env['account.account'].with_company(branch.id).create({
            'name': 'STCK Test Account',
            'code': '100119',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        self.category_standard_auto.with_company(branch.id).property_valuation = "real_time"
        self.category_standard_auto.with_company(branch.id).property_stock_valuation_account_id = test_account

        bill = self._create_bill(product=product, post=False, company_id=branch.id)
        self.assertEqual(bill.invoice_line_ids.account_id, test_account)

    def test_apply_inventory_adjustment_on_multiple_quants_simultaneously(self):
        product = self.product_standard_auto
        product_b = product.copy()
        products = product + product_b

        self._use_inventory_location_accounting()

        self.env['stock.quant']._update_available_quantity(product, self.stock_location, 5)
        self.env['stock.quant']._update_available_quantity(product_b, self.stock_location, 15)

        quants = products.stock_quant_ids
        quants.inventory_quantity = 10.0
        wizard = self.env['stock.inventory.adjustment.name'].create({'quant_ids': quants})
        wizard.action_apply()
        inv_adjustment_journal_items = self.env['account.move.line'].search([('product_id', 'in', products.ids)], order='id asc', limit=4)
        prod_a_accounts = product.product_tmpl_id.get_product_accounts()
        prod_b_accounts = product_b.product_tmpl_id.get_product_accounts()
        self.assertRecordValues(
            inv_adjustment_journal_items,
            [
                {'account_id': self.account_inventory.id, 'product_id': product.id},
                {'account_id': prod_a_accounts['stock_valuation'].id, 'product_id': product.id},
                {'account_id': prod_b_accounts['stock_valuation'].id, 'product_id': product_b.id},
                {'account_id': self.account_inventory.id, 'product_id': product_b.id},
            ]
        )

    @freeze_time("2020-01-22")
    def test_backdate_picking_with_lock_date(self):
        """
        Check that pickings can not be backdate or validated prior to the
        fiscal and hard lock date.
        """
        self.env['account.lock_exception'].search([]).sudo().unlink()
        lock_date = fields.Date.from_string('2011-01-01')
        prior_to_lock_date = fields.Datetime.add(lock_date, days=-1)
        post_to_lock_date = fields.Datetime.add(lock_date, days=+1)
        self.env['stock.quant']._update_available_quantity(self.product_standard, self.stock_location, 10)

        receipt_not_done = self._make_in_move(
            product=self.product_standard, quantity=1, create_picking=True, auto_validate=False
        ).picking_id
        receipt_done = self._make_in_move(
            product=self.product_standard, quantity=1, create_picking=True
        ).picking_id
        # Check that the purchase, sale and tax lock dates do not impose any restrictions
        self.env.company.write({
            'sale_lock_date': lock_date,
            'purchase_lock_date': lock_date,
            'tax_lock_date': lock_date,
        })
        # Receipts can be backdated
        receipt_not_done.scheduled_date = prior_to_lock_date
        receipt_done.date_done = prior_to_lock_date

        # Check that the fiscal year lock date imposes restrictions
        self.env.company.write({
            'sale_lock_date': False,
            'purchase_lock_date': False,
            'tax_lock_date': False,
            'fiscalyear_lock_date': lock_date,
        })
        # Receipts can not be backdated prior to lock date
        receipt_not_done.scheduled_date = post_to_lock_date
        receipt_done.date_done = post_to_lock_date
        # Lock dates should not affect un-validated scheduled_date
        receipt_not_done.scheduled_date = prior_to_lock_date
        with self.assertRaises(UserError):
            receipt_done.date_done = prior_to_lock_date

        # Check that the hard lock date imposes restrictions
        self.env.company.write({
            'fiscalyear_lock_date': False,
            'hard_lock_date': lock_date,
        })
        # Receipts can not be backdated prior to lock date
        receipt_not_done.scheduled_date = post_to_lock_date
        receipt_done.date_done = post_to_lock_date
        # Lock dates should not affect un-validated scheduled_date
        receipt_not_done.scheduled_date = prior_to_lock_date
        with self.assertRaises(UserError):
            receipt_done.date_done = prior_to_lock_date

    def test_invoice_with_journal_item_without_label(self):
        """Test posting an invoice whose invoice lines have no label.
        The 'name' field is optional on account.move.line and should be
        handled safely when generating accounting entries.
        """
        move = self._create_invoice(product=self.product_standard)
        # name should remain falsy on the invoice line
        self.assertFalse(move.invoice_line_ids.name)
        # ensure the invoice is posted successfully
        self.assertEqual(move.state, 'posted')
