from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMovePaymentMethod(TestItEdi):

    _test_user_groups = None  # FIXME list needed groups

    def test_account_move_payment_method(self):
        payment_method = self.env['account.payment.method'].sudo().create({
            'name': 'Test Payment Method',
            'code': 'test_payment_method',
            'payment_type': 'inbound',
        })

        payment_method_line = self.env['account.payment.method.line'].create({
            'name': 'new payment method line',
            'payment_method_id': payment_method.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'l10n_it_payment_method': 'MP07',
        })

        move = self.init_invoice('out_invoice', amounts=[1000], post=True)

        # When partner don't set payment method , it should default to MP05.
        self.assertEqual(move.l10n_it_payment_method, 'MP05')

        self.partner_a.property_inbound_payment_method_line_id = payment_method_line
        move.partner_id = self.partner_a

        self.assertEqual(move.l10n_it_payment_method, 'MP07')

        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).create({})

        self.assertEqual(
            wizard.payment_method_line_id,
            payment_method_line,
            "The wizard should select the payment method line matching the invoice's Italian payment method.",
        )
