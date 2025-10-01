from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMovePaymentMethod(TestItEdi):

    def test_account_move_payment_method(self):
        move = self.init_invoice("out_invoice", amounts=[1000], post=True)
        # When the move is created we put the default value MP05
        self.assertEqual(move.l10n_it_payment_method, 'MP05')

        payment_method = self.env['account.payment.method'].sudo().create({
            'name': 'Test Payment Method',
            'code': 'manual',
            'payment_type': 'inbound',
            'l10n_it_payment_method': 'MP07',
        })

        # When registering a payment with a payment method, the payment method on the move will be overwritten
        self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).create({
            'payment_method_id': payment_method.id,
        })._create_payments()

        self.assertEqual(move.l10n_it_payment_method, 'MP07')
