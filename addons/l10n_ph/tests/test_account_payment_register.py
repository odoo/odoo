# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPhAccountPaymentRegister(TestPhCommon):

    def test_default_withhold_is_always_withhold_and_pay(self):
        """ PH always withholds and pays when a withholding tax applies, even in the case where
        the generic engine would otherwise propose a withhold-only payment (the invoice's net
        amount already settled by another payment, only the withholding itself remaining). """
        withholding_tax = self.env['account.tax'].create({
            'name': '10% Withholding',
            'amount_type': 'percent',
            'amount': -10.0,
            'type_tax_use': 'purchase',
            'is_withholding_tax': True,
        })
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'invoice_date': '2026-06-01',
            'invoice_line_ids': [Command.create({
                'name': 'Product Line',
                'price_unit': 1000.0,
                'tax_ids': [Command.set(withholding_tax.ids)],
            })],
        })
        bill.action_post()

        # Pay the net amount only, leaving just the withholding tax outstanding: the generic
        # engine would default to 'withhold' (withhold-only) in that situation.
        register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=bill.ids)\
            .create({'withhold': 'payment'})
        register._create_payments()

        self.assertEqual(bill.withholding_residual_amount_currency, 100.0)
        self.assertEqual(bill.withholding_net_residual_amount_currency, 0.0)
        self.assertEqual(
            self.env['account.payment.register']._get_default_withhold(bill),
            'withhold_pay',
        )
