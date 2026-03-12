# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTHWTHPayment(AccountTestInvoicingCommon):
    """ Test the payment flows """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('th')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].withholding_tax_base_account_id = cls.env['account.account'].create({
            'code': 'WITHB',
            'name': 'Withholding Tax Base Account',
            'reconcile': True,
            'account_type': 'asset_current',
        })
        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        cls.outstanding_account = cls.env['account.account'].create({
            'name': "Outstanding Payments",
            'code': 'OSTP420',
            'reconcile': False,
            'account_type': 'asset_current',
        })

    def test_withholding_condition_is_propagated(self):
        withholding_tax = self.percent_tax(-1, is_withholding_tax_on_payment=True, withholding_sequence_id=self.withholding_sequence.id)

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(withholding_tax.ids)],
            })],
        })
        invoice.action_post()
        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})
        # Assert that the computation set the default as expected.
        self.assertEqual(payment_register.l10n_th_wth_condition, 'at_source')
        payment_register.l10n_th_wth_condition = 'one_time'
        payment = payment_register._create_payments()
        # Assert that the manually set condition was propagated to the payment as expected.
        self.assertEqual(payment.l10n_th_wth_condition, 'one_time')
