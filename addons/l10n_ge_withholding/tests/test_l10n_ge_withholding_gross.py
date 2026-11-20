from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import TestL10nGeWithholdingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nGeWithholdingGross(TestL10nGeWithholdingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_vat = cls.env['account.chart.template'].with_company(cls.company_data['company']).ref('ge_vat_purchase_18')
        cls.tax_dividends.l10n_ge_is_gross = True
        cls.tax_account = cls.tax_dividends.invoice_repartition_line_ids.account_id
        cls.gross_account = cls.company_data['company'].l10n_ge_withholding_gross_account_id

    def _get_withholding_lines(self, payment):
        return payment.move_id.line_ids.filtered(lambda line: line.account_id in self.tax_account + self.gross_account).sorted('balance')

    def test_gross_toggle_recomputes_draft_bills(self):
        self.tax_dividends.l10n_ge_is_gross = False
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids)
        self.assertRecordValues(bill, [{
            'withholding_residual_amount_currency': 50.0,
            'l10n_ge_gross_withholding_amount_currency': 0.0,
            'withholding_net_residual_amount_currency': 950.0,
        }])

        self.tax_dividends.l10n_ge_is_gross = True
        self.assertRecordValues(bill, [{
            'withholding_residual_amount_currency': 52.63,
            'l10n_ge_gross_withholding_amount_currency': 52.63,
            'withholding_net_residual_amount_currency': 1000.0,
        }])

    def test_gross_locked_on_posted_bills(self):
        """ Gross can be changed while the tax is only on draft bills, not once a posted bill uses it. """
        self.tax_dividends.l10n_ge_is_gross = False
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids)
        self.assertFalse(self.tax_dividends.l10n_ge_is_gross_locked)
        self.tax_dividends.l10n_ge_is_gross = True
        self.tax_dividends.l10n_ge_is_gross = False

        bill.action_post()
        self.tax_dividends.invalidate_recordset(['l10n_ge_is_gross_locked'])
        self.assertTrue(self.tax_dividends.l10n_ge_is_gross_locked)
        with self.assertRaises(UserError):
            self.tax_dividends.l10n_ge_is_gross = True
        self.tax_dividends.l10n_ge_is_gross = False

    def test_gross_only_on_georgian_purchase_withholding_percentage_tax(self):
        """ Gross is refused outside Georgia, on a sale, tax included or fixed tax, at a positive rate or 100% and without withholding. """
        country_us = self.env.ref('base.us')
        tax_group_us = self.env['account.tax.group'].create({'name': "US", 'country_id': country_us.id})
        self.tax_dividends.copy({'l10n_ge_is_gross': False, 'country_id': country_us.id, 'tax_group_id': tax_group_us.id})
        for vals in ({'country_id': country_us.id, 'tax_group_id': tax_group_us.id}, {'type_tax_use': 'sale'}, {'price_include_override': 'tax_included'}, {'amount_type': 'fixed'}, {'amount': 5.0}, {'amount': -100.0}, {'is_withholding_tax': False, 'amount': 5.0}):
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                self.tax_dividends.copy(vals)

    def test_gross_withholding_tax_alone_on_line(self):
        """ A gross withholding tax cannot share a line with another withholding tax, but can with VAT. """
        self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=(self.tax_dividends + self.tax_vat).ids)
        with self.assertRaises(ValidationError):
            self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=(self.tax_dividends + self.tax_interest).ids)

    def test_gross_payment(self):
        """ The vendor receives the full amount: the company books the gross withholding as a cost. """
        self.assertEqual(self.gross_account.code, '740900')
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids, post=True)
        wizard = self._register_payment(bill)
        self.assertRecordValues(wizard, [{'withhold': 'withhold_pay', 'amount': 1000.0, 'withholding_net_amount': 1000.0}])
        self.assertRecordValues(wizard.withholding_line_ids, [{'base_amount': 1052.63, 'amount': 52.63}])
        payment = wizard._create_payments()
        self.assertRecordValues(payment, [{'amount': 1000.0, 'withholding_net_amount': 1000.0}])
        self.assertRecordValues(self._get_withholding_lines(payment), [
            {'account_id': self.tax_account.id, 'balance': -52.63, 'tax_base_amount': -1052.63},
            {'account_id': self.gross_account.id, 'balance': 52.63, 'tax_base_amount': 0.0},
        ])
        self.assertEqual(sum(payment.move_id.line_ids.filtered(lambda line: line.account_id == self.outstanding_account).mapped('balance')), -1000.0)
        self.assertRecordValues(bill, [{'payment_state': 'paid', 'withholding_residual_amount_currency': 0.0}])

    def test_gross_payment_reset_to_draft(self):
        """ The base of the payment entry is already grossed up: resetting it to draft and posting it again doesn't gross it up twice. """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids, post=True)
        payment = self._register_payment(bill)._create_payments()
        # account.payment.register leaves `skip_invoice_sync` in the context, rebrowse as the web client would.
        payment = self.env['account.payment'].browse(payment.id)
        payment.action_draft()
        payment.action_post()
        self.assertRecordValues(self._get_withholding_lines(payment), [
            {'account_id': self.tax_account.id, 'balance': -52.63, 'tax_base_amount': 1052.63},
            {'account_id': self.gross_account.id, 'balance': 52.63, 'tax_base_amount': 0.0},
        ])

    def test_gross_withholding_rounded_per_line(self):
        """ With rounding per line, the gross withholding is computed on the grossed-up base, not by scaling the rounded tax. """
        self.company_data['company'].tax_calculation_rounding_method = 'round_per_line'
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=10.30, tax_ids=self.tax_dividends.ids)
        self.assertRecordValues(bill, [{'withholding_total_amount_currency': 0.54, 'l10n_ge_gross_withholding_amount_currency': 0.54}])

    def test_gross_and_deducted_withholding_payment(self):
        """ Only the deducted withholding is taken from the vendor. """
        bill = self._create_invoice(move_type='in_invoice', post=True, invoice_line_ids=[
            self._prepare_invoice_line(price_unit=1000.0, tax_ids=self.tax_dividends.ids),
            self._prepare_invoice_line(price_unit=2000.0, tax_ids=self.tax_interest.ids),
        ])
        self.assertRecordValues(bill, [{
            'withholding_total_amount_currency': 152.63,
            'l10n_ge_gross_withholding_amount_currency': 52.63,
            'withholding_net_residual_amount_currency': 2900.0,
        }])
        payment = self._register_payment(bill)._create_payments()
        self.assertRecordValues(payment, [{'amount': 3000.0, 'withholding_net_amount': 2900.0}])
        self.assertRecordValues(self._get_withholding_lines(payment), [
            {'tax_line_id': self.tax_interest.id, 'balance': -100.0},
            {'tax_line_id': self.tax_dividends.id, 'balance': -52.63},
            {'tax_line_id': False, 'balance': 52.63},
        ])
        self.assertEqual(sum(payment.move_id.line_ids.filtered(lambda line: line.account_id == self.outstanding_account).mapped('balance')), -2900.0)

    def test_gross_manual_payment(self):
        """ On a payment without bill, the base typed by hand is the gross base. """
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_a.id,
            'amount': 1000.0,
            'withhold': 'withhold_pay',
            'withholding_line_ids': [Command.create({'tax_id': self.tax_dividends.id, 'base_amount': 1052.63})],
        })
        self.assertRecordValues(payment.withholding_line_ids, [{'amount': 52.63}])
        self.assertRecordValues(payment, [{'withholding_net_amount': 1000.0}])
        payment.action_post()
        self.assertRecordValues(self._get_withholding_lines(payment), [
            {'account_id': self.tax_account.id, 'balance': -52.63},
            {'account_id': self.gross_account.id, 'balance': 52.63},
        ])

    def test_gross_payment_only_withhold_and_pay(self):
        """ A gross bill can't be paid without withholding, nor withheld without paying. """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids, post=True)
        with self.assertRaisesRegex(ValidationError, "For lines with a gross withholding tax"):
            self._register_payment(bill, withhold='withhold')._create_payments()
        with self.assertRaisesRegex(UserError, "For bills and credit notes with a gross withholding tax"):
            self._register_payment(bill, withhold='payment')._create_payments()

        bill_2 = self._create_invoice_one_line(move_type='in_invoice', price_unit=500.0, tax_ids=self.tax_dividends.ids, post=True)
        with self.assertRaisesRegex(UserError, "Tick Group Payments"):
            self._register_payment(bill + bill_2, group_payment=False)._create_payments()

    def test_gross_bill_and_credit_note(self):
        """ A bill and its credit note are paid separately: the credit note reverses its share of the gross withholding. """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids, post=True)
        refund = self._create_invoice_one_line(move_type='in_refund', price_unit=200.0, tax_ids=self.tax_dividends.ids, post=True)
        with self.assertRaisesRegex(UserError, "Register the payments of the bills and the credit notes separately"):
            self._register_payment(bill + refund)._create_payments()

        payment = self._register_payment(refund)._create_payments()
        self.assertRecordValues(payment, [{'payment_type': 'inbound', 'amount': 200.0, 'withholding_net_amount': 200.0}])
        self.assertRecordValues(self._get_withholding_lines(payment), [
            {'account_id': self.gross_account.id, 'balance': -10.53},
            {'account_id': self.tax_account.id, 'balance': 10.53},
        ])
        self._register_payment(bill)._create_payments()
        self.assertRecordValues(bill + refund, [
            {'payment_state': 'paid', 'withholding_residual_amount_currency': 0.0},
            {'payment_state': 'paid', 'withholding_residual_amount_currency': 0.0},
        ])

    def test_gross_payment_without_cost_account(self):
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, tax_ids=self.tax_dividends.ids, post=True)
        self.company_data['company'].l10n_ge_withholding_gross_account_id = False
        with self.assertRaisesRegex(UserError, "Set the Gross Withholding Cost account"):
            self._register_payment(bill)._create_payments()
