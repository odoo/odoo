# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install_l10n', 'post_install', '-at_install')
class ISRTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ch'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def print_isr(self, invoice):
        try:
            invoice.action_invoice_sent()
            return True
        except ValidationError:
            return False

    def test_l10n_ch_postals(self):

        def assertBankAccountValid(account_number, expected_account_type, expected_postal=None):
            partner_bank = self.env['res.partner.bank'].create({
                'acc_number': account_number,
                'partner_id': self.partner_a.id,
            })
            expected_vals = {'acc_type': expected_account_type}
            if expected_postal is not None:
                expected_vals['l10n_ch_postal'] = expected_postal

            self.assertRecordValues(partner_bank, [expected_vals])

        assertBankAccountValid('010391391', 'postal', expected_postal='010391391')
        assertBankAccountValid('CH6309000000250097798', 'iban', expected_postal='25-9779-8')
        assertBankAccountValid('GR1601101250000000012300695', 'iban', expected_postal=False)

        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': '010391394',
            'partner_id': self.partner_a.id,
        })
        self.assertNotEqual(partner_bank.acc_type, 'postal')

    def test_isr(self):
        isr_bank_account = self.env['res.partner.bank'].create({
            'acc_number': "ISR {} number",
            'partner_id': self.env.company.partner_id.id,
            'l10n_ch_isr_subscription_chf': '01-39139-1',
        })

        invoice_chf = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'partner_bank_id': isr_bank_account.id,
            'currency_id': self.env.ref('base.CHF').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        invoice_chf.action_post()
        self.assertTrue(self.print_isr(invoice_chf))
        self.env.ref('base.EUR').active = True
        invoice_eur = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'partner_bank_id': isr_bank_account.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        invoice_eur.action_post()
        #a normal invoice will still get printed
        self.assertTrue(self.print_isr(invoice_eur))
        # However, a isr bill can't be printed with those infos
        self.assertFalse(invoice_eur.l10n_ch_isr_valid)
