from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingWithBanksCommon


@tagged('post_install', '-at_install')
class TestPaymentReceipt(AccountTestInvoicingWithBanksCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        cls.epd_term = cls.env['account.payment.term'].create({
            'name': '5% 10 Net 30',
            'early_discount': True,
            'discount_days': 10,
            'discount_percentage': 5.0,
            'line_ids': [Command.create({
                'value': 'percent',
                'value_amount': 100,
                'delay_type': 'days_after',
                'nb_days': 30,
            })],
        })
        cls.no_epd_term = cls.env['account.payment.term'].create({
            'name': 'Net 30',
            'line_ids': [Command.create({
                'value': 'percent',
                'value_amount': 100,
                'delay_type': 'days_after',
                'nb_days': 30,
            })],
        })

    def test_epd_split_signs(self):
        """ Test that an early payment discount adds a discount row, signed for
        both bills and invoices.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'tax_ids': [],
            })],
        })
        (bill + invoice).action_post()

        bill_payment = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({'payment_date': '2026-01-05'})._create_payments()
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({'payment_date': '2026-01-05'})._create_payments()

        bill_rows = bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(bill_rows), 2)
        self.assertAlmostEqual(bill_rows[0]['amount_invoice'], -95.0)
        self.assertEqual(bill_rows[1]['name'], "Early Payment Discount")
        self.assertAlmostEqual(bill_rows[1]['amount_invoice'], -5.0)
        self.assertEqual(bill.amount_residual, 0.0)

        inv_rows = invoice._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(inv_rows), 2)
        self.assertAlmostEqual(inv_rows[0]['amount_invoice'], 190.0)
        self.assertAlmostEqual(inv_rows[1]['amount_invoice'], -10.0)
        self.assertEqual(invoice.amount_residual, 0.0)

        report = self.env.ref('account.action_report_payment_receipt')
        html, _ = self.env['ir.actions.report']._render_qweb_html(report.id, bill_payment.ids)
        self.assertIn('Early Payment Discount', html.decode() if isinstance(html, bytes) else html)

    def test_epd_split_with_tax_reduction(self):
        """ Test an early payment discount with tax reduction. """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            })],
        })
        bill.action_post()

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({'payment_date': '2026-01-05'})._create_payments()

        rows = bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]['amount_invoice'], -109.25)
        self.assertEqual(rows[1]['name'], "Early Payment Discount")
        self.assertAlmostEqual(rows[1]['amount_invoice'], -5.75)
        self.assertEqual(bill.amount_residual, 0.0)

    def test_no_split_cases(self):
        """ Test that the receipt keeps a single row without an early payment
        discount, for a partial payment, or past the discount window.
        """
        no_epd_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-15',
            'invoice_date': '2026-01-15',
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        partial_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-15',
            'invoice_date': '2026-01-15',
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300.0,
                'tax_ids': [],
            })],
        })
        past_window_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2025-12-15',
            'invoice_date': '2025-12-15',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        in_window_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-10',
            'invoice_date': '2026-01-10',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        (no_epd_bill + partial_bill + past_window_bill + in_window_bill).action_post()

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=no_epd_bill.ids,
        ).create({'payment_date': '2026-01-15'})._create_payments()
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=partial_bill.ids,
        ).create({'amount': 55.0, 'payment_date': '2026-01-15'})._create_payments()
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(past_window_bill + in_window_bill).ids,
        ).create({'group_payment': True, 'payment_date': '2026-01-15'})._create_payments()

        no_epd_rows = no_epd_bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(no_epd_rows), 1)
        self.assertAlmostEqual(no_epd_rows[0]['amount_invoice'], -100.0)

        partial_rows = partial_bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(partial_rows), 1)
        self.assertAlmostEqual(partial_rows[0]['amount_invoice'], -55.0)

        self.assertEqual(len(past_window_bill._get_reconciled_invoices_partials_for_receipt()), 1)

        in_window_rows = in_window_bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(in_window_rows), 2)
        self.assertEqual(in_window_rows[1]['name'], "Early Payment Discount")

    def test_multi_currency(self):
        """ Test that the paid amount is shown in the payment's currency, with
        and without an early payment discount.
        """
        non_epd_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        epd_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        (non_epd_bill + epd_bill).action_post()

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=non_epd_bill.ids,
        ).create({'payment_date': '2026-01-05'})._create_payments()
        epd_payment = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=epd_bill.ids,
        ).create({'payment_date': '2026-01-05'})._create_payments()

        non_epd_rows = non_epd_bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(non_epd_rows), 1)
        self.assertEqual(non_epd_rows[0]['currency_payment'], self.other_currency)
        self.assertAlmostEqual(non_epd_rows[0]['amount_payment'], -100.0)

        epd_rows = epd_bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(epd_rows), 2)
        self.assertEqual(epd_rows[0]['currency_payment'], self.other_currency)
        self.assertAlmostEqual(epd_rows[0]['amount_invoice'], -95.0)
        self.assertAlmostEqual(epd_rows[0]['amount_payment'], -100.0)
        self.assertAlmostEqual(epd_rows[1]['amount_invoice'], -5.0)
        self.assertFalse(epd_rows[1]['currency_payment'])

        report = self.env.ref('account.action_report_payment_receipt')
        html, _ = self.env['ir.actions.report']._render_qweb_html(report.id, epd_payment.ids)
        self.assertIn('Early Payment Discount', html.decode() if isinstance(html, bytes) else html)

    def test_write_off_on_cash_discount_account(self):
        """ Test that a write-off booked on the cash discount account within the
        discount window is reported as a write-off, not as an early payment
        discount.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        bill.action_post()

        gain_account = self.env.company.account_journal_early_pay_discount_gain_account_id
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({
            'amount': 60.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': gain_account.id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-05',
        })._create_payments()

        rows = bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]['amount_invoice'], -60.0)
        self.assertEqual(rows[1]['name'], 'Write-Off')
        self.assertAlmostEqual(rows[1]['amount_invoice'], -40.0)
        self.assertEqual(bill.amount_residual, 0.0)

    def test_write_off_split(self):
        """ Test that a payment below a fully-paid bill's total adds a write-off
        row for the difference.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'tax_ids': [],
            })],
        })
        paid_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        (bill + paid_bill).action_post()

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({
            'amount': 150.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-15',
        })._create_payments()
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=paid_bill.ids,
        ).create({'payment_date': '2026-01-15'})._create_payments()

        rows = bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]['amount_invoice'], -150.0)
        self.assertEqual(rows[1]['name'], 'Write-Off')
        self.assertAlmostEqual(rows[1]['amount_invoice'], -50.0)
        self.assertEqual(bill.amount_residual, 0.0)

        paid_rows = paid_bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(paid_rows), 1)
        self.assertAlmostEqual(paid_rows[0]['amount_invoice'], -100.0)

    def test_write_off_grouped_split(self):
        """ Test that a grouped payment's write-off is split across the bills in
        proportion to their amounts.
        """
        bill_a = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'tax_ids': [],
            })],
        })
        bill_b = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300.0,
                'tax_ids': [],
            })],
        })
        (bill_a + bill_b).action_post()

        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(bill_a + bill_b).ids,
        ).create({
            'group_payment': True,
            'amount': 480.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-15',
        })._create_payments()

        rows_a = bill_a._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows_a), 2)
        self.assertAlmostEqual(rows_a[0]['amount_invoice'], -192.0)
        self.assertAlmostEqual(rows_a[0]['amount_payment'], -192.0)
        self.assertAlmostEqual(rows_a[1]['amount_invoice'], -8.0)

        rows_b = bill_b._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows_b), 2)
        self.assertAlmostEqual(rows_b[0]['amount_invoice'], -288.0)
        self.assertAlmostEqual(rows_b[0]['amount_payment'], -288.0)
        self.assertAlmostEqual(rows_b[1]['amount_invoice'], -12.0)

        self.assertEqual(bill_a.amount_residual, 0.0)
        self.assertEqual(bill_b.amount_residual, 0.0)

    def test_write_off_split_multi_currency(self):
        """ Test that a write-off on a foreign-currency bill paid in the company
        currency shows the paid amount in the payment's currency, not scaled by
        the exchange rate.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'tax_ids': [],
            })],
        })
        bill.action_post()

        # Bill is 200 EUR (= 100 USD at rate 2.0). Pay 96 USD cash, write off
        # the remaining 4 USD to fully reconcile it.
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids,
        ).create({
            'currency_id': self.company.currency_id.id,
            'amount': 96.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-15',
        })._create_payments()

        rows = bill._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['currency_invoice'], self.other_currency)
        self.assertEqual(rows[0]['currency_payment'], self.company.currency_id)
        self.assertAlmostEqual(rows[0]['amount_invoice'], -192.0)  # EUR
        self.assertAlmostEqual(rows[0]['amount_payment'], -96.0)  # USD
        self.assertEqual(rows[1]['name'], 'Write-Off')
        self.assertAlmostEqual(rows[1]['amount_invoice'], -8.0)  # EUR
        self.assertEqual(bill.amount_residual, 0.0)

    def test_write_off_grouped_split_multi_currency(self):
        """ Test that a grouped write-off on foreign-currency bills paid in the
        company currency splits the write-off per bill and reports the paid
        amount in the payment's currency, not scaled by the exchange rate.
        """
        bill_a = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'tax_ids': [],
            })],
        })
        bill_b = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.no_epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 300.0,
                'tax_ids': [],
            })],
        })
        (bill_a + bill_b).action_post()

        # Bills are 200 + 300 EUR (= 250 USD at rate 2.0). Pay 240 USD and write
        # off the remaining 10 USD, split 2 / 3 across the bills.
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(bill_a + bill_b).ids,
        ).create({
            'group_payment': True,
            'currency_id': self.company.currency_id.id,
            'amount': 240.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-15',
        })._create_payments()

        rows_a = bill_a._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows_a), 2)
        self.assertAlmostEqual(rows_a[0]['amount_invoice'], -192.0)  # EUR
        self.assertAlmostEqual(rows_a[0]['amount_payment'], -96.0)  # USD
        self.assertAlmostEqual(rows_a[1]['amount_invoice'], -8.0)  # EUR

        rows_b = bill_b._get_reconciled_invoices_partials_for_receipt()
        self.assertEqual(len(rows_b), 2)
        self.assertAlmostEqual(rows_b[0]['amount_invoice'], -288.0)  # EUR
        self.assertAlmostEqual(rows_b[0]['amount_payment'], -144.0)  # USD
        self.assertAlmostEqual(rows_b[1]['amount_invoice'], -12.0)  # EUR

        self.assertEqual(bill_a.amount_residual, 0.0)
        self.assertEqual(bill_b.amount_residual, 0.0)
