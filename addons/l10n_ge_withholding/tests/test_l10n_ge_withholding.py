from odoo import Command
from odoo.tests import tagged

from .common import TestL10nGeWithholdingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nGeWithholding(TestL10nGeWithholdingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_eur = cls.setup_other_currency('EUR', rates=[('1900-01-01', 1 / 3)])

    def _register_payment_with_withholding(self, bill, withholding_lines_vals=None):
        payment_register = self._register_payment(bill)
        if withholding_lines_vals is not None:
            payment_register.withhold = 'withhold_pay'
            payment_register.withholding_line_ids = [Command.clear()] + [Command.create(line_vals) for line_vals in withholding_lines_vals]
        return payment_register._create_payments()

    def test_treaty_exempt_amount_on_withholding_tax_line(self):
        """ The treaty exempt amount of the withholding lines is carried onto the withholding tax journal item
        in company currency, converted and signed like its base amount, and summed over merged lines.
        """
        bill = self._create_invoice_one_line(move_type='in_invoice', currency_id=self.currency_eur, price_unit=11000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_services.id, 'base_amount': 6000.0, 'l10n_ge_treaty_exempt_amount': 100.0},
            {'tax_id': self.tax_services.id, 'base_amount': 4000.0, 'l10n_ge_treaty_exempt_amount': 50.0},
            {'tax_id': self.tax_dividends.id, 'base_amount': 1000.0},
        ])
        withholding_tax_lines = payment.move_id.line_ids.filtered('tax_line_id').sorted('balance')
        self.assertRecordValues(withholding_tax_lines, [
            {
                'tax_line_id': self.tax_services.id,
                'amount_currency': -1000.0,
                'balance': -3000.0,
                'tax_base_amount': -30000.0,
                'l10n_ge_treaty_exempt_amount': -450.0,
            },
            {
                'tax_line_id': self.tax_dividends.id,
                'amount_currency': -50.0,
                'balance': -150.0,
                'tax_base_amount': -3000.0,
                'l10n_ge_treaty_exempt_amount': 0.0,
            },
        ])
        other_lines = payment.move_id.line_ids - withholding_tax_lines
        self.assertFalse(any(other_lines.mapped('l10n_ge_treaty_exempt_amount')))

    def test_treaty_exempt_amount_on_refund_payment(self):
        """ On the payment of a credit note, the treaty exempt amount follows the sign of the base amount. """
        credit_note = self._create_invoice_one_line(move_type='in_refund', price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(credit_note, [
            {'tax_id': self.tax_services.id, 'base_amount': 1000.0, 'l10n_ge_treaty_exempt_amount': 40.0},
        ])
        self.assertRecordValues(payment.move_id.line_ids.filtered('tax_line_id'), [{
            'balance': 100.0,
            'tax_base_amount': 1000.0,
            'l10n_ge_treaty_exempt_amount': 40.0,
        }])

    def test_treaty_exempt_amount_kept_after_reset_to_draft(self):
        """ The treaty exempt amount stays on the withholding tax journal item when account._sync_tax_lines replaces it, on the second reset to draft. """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_services.id, 'base_amount': 1000.0, 'l10n_ge_treaty_exempt_amount': 20.0},
        ])
        # account.payment.register leaves `skip_invoice_sync` in the context, rebrowse as the web client would.
        payment = self.env['account.payment'].browse(payment.id)
        tax_line = payment.move_id.line_ids.filtered('tax_line_id')
        for _i in range(2):
            payment.action_draft()
            payment.action_post()
        self.assertNotEqual(payment.move_id.line_ids.filtered('tax_line_id'), tax_line)
        self.assertRecordValues(payment.move_id.line_ids.filtered('tax_line_id'), [{'l10n_ge_treaty_exempt_amount': -20.0}])

    def test_treaty_exempt_amount_changed_on_draft_payment(self):
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_services.id, 'base_amount': 1000.0, 'l10n_ge_treaty_exempt_amount': 20.0},
        ])
        payment = self.env['account.payment'].browse(payment.id)
        payment.action_draft()
        payment.withholding_line_ids.l10n_ge_treaty_exempt_amount = 30.0
        payment.action_post()
        self.assertRecordValues(payment.move_id.line_ids.filtered('tax_line_id'), [{'l10n_ge_treaty_exempt_amount': -30.0}])

    def test_treaty_exempt_amount_on_reversed_payment(self):
        """ Reversing a payment entry reverses the base and the treaty exempt amount of its withholding tax journal item too. """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_services.id, 'base_amount': 1000.0, 'l10n_ge_treaty_exempt_amount': 20.0},
        ])
        reversal = payment.move_id._reverse_moves(cancel=True)
        self.assertRecordValues((payment.move_id + reversal).line_ids.filtered('tax_line_id'), [
            {'balance': -100.0, 'tax_base_amount': -1000.0, 'l10n_ge_treaty_exempt_amount': -20.0},
            {'balance': 100.0, 'tax_base_amount': 1000.0, 'l10n_ge_treaty_exempt_amount': 20.0},
        ])

    def test_treaty_exempt_amount_per_analytic_distribution(self):
        """ Withholding lines of one tax with different analytic distributions give one withholding tax journal
        item each, and each item only carries the treaty exempt amount of its own lines.
        """
        analytic_plan = self.env['account.analytic.plan'].create({'name': "Plan"})
        analytic_account_1, analytic_account_2 = self.env['account.analytic.account'].create([
            {'name': "Account 1", 'plan_id': analytic_plan.id},
            {'name': "Account 2", 'plan_id': analytic_plan.id},
        ])
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=10000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_services.id, 'base_amount': 6000.0, 'l10n_ge_treaty_exempt_amount': 100.0, 'analytic_distribution': {str(analytic_account_1.id): 100.0}},
            {'tax_id': self.tax_services.id, 'base_amount': 4000.0, 'l10n_ge_treaty_exempt_amount': 50.0, 'analytic_distribution': {str(analytic_account_2.id): 100.0}},
        ])
        self.assertRecordValues(payment.move_id.line_ids.filtered('tax_line_id').sorted('balance'), [
            {'balance': -600.0, 'analytic_distribution': {str(analytic_account_1.id): 100.0}, 'l10n_ge_treaty_exempt_amount': -100.0},
            {'balance': -400.0, 'analytic_distribution': {str(analytic_account_2.id): 100.0}, 'l10n_ge_treaty_exempt_amount': -50.0},
        ])

    def test_zero_withholding_tax_line_kept(self):
        """ A withholding fully exempted by a treaty still gets its withholding tax journal item, at zero,
        with its return grid and treaty exempt amount.
        """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_dividends.id, 'base_amount': 1000.0, 'amount': 0.0, 'l10n_ge_treaty_exempt_amount': 50.0},
        ])
        self.assertRecordValues(payment.move_id.line_ids.filtered('tax_line_id'), [{
            'tax_line_id': self.tax_dividends.id,
            'balance': 0.0,
            'tax_base_amount': -1000.0,
            'tax_tag_ids': self._get_tag('1(T)_W_D').ids,
            'l10n_ge_treaty_exempt_amount': -50.0,
        }])

    def test_withholding_tax_grids(self):
        """ A withholding tax puts its return grids on the base and tax journal items of the payment. """
        bill = self._create_invoice_one_line(move_type='in_invoice', price_unit=1000.0, post=True)
        payment = self._register_payment_with_withholding(bill, [
            {'tax_id': self.tax_dividends.id, 'base_amount': 1000.0},
        ])
        lines = payment.move_id.line_ids
        self.assertRecordValues(lines.filtered('tax_ids'), [
            {'balance': 1000.0, 'tax_tag_ids': self._get_tag('1(B)_W_D').ids},
        ])
        self.assertRecordValues(lines.filtered('tax_line_id'), [
            {'balance': -50.0, 'tax_tag_ids': self._get_tag('1(T)_W_D').ids},
        ])

    def test_withholding_taxes_restricted_to_partner_categories(self):
        """ The categories of a contact, shared with its child contacts, restrict the withholding taxes offered on its payments. """
        category = self.env.ref('l10n_ge_withholding.wht_category_31')
        self.partner_a.l10n_ge_wht_category_ids = category
        child = self.env['res.partner'].create({'name': "Child", 'parent_id': self.partner_a.id})
        self.assertEqual(child.l10n_ge_wht_category_ids, category)

        for partner, expected_domain in ((self.partner_a, [['l10n_ge_wht_category_ids', 'in', category.ids]]), (self.partner_b, [])):
            with self.subTest(partner=partner.name):
                bill = self._create_invoice_one_line(move_type='in_invoice', partner_id=partner.id, price_unit=1000.0, post=True)
                wizard = self._register_payment(bill, withhold='withhold_pay')
                wizard.withholding_line_ids = [Command.create({'tax_id': self.tax_dividends.id, 'base_amount': 1000.0})]
                self.assertEqual(wizard.withholding_line_ids.l10n_ge_tax_id_domain or [], expected_domain)
        self.assertIn(self.tax_dividends, self.env['account.tax'].search([('l10n_ge_wht_category_ids', 'in', category.ids)]))
        self.assertNotIn(self.tax_services, self.env['account.tax'].search([('l10n_ge_wht_category_ids', 'in', category.ids)]))
