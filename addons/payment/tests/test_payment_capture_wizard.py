# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('post_install', '-at_install')
class TestPaymentCaptureWizard(PaymentCommon):

    def test_partial_capture_wizard(self):
        self.provider.update({
            'capture_manually': True,
            'support_manual_capture': 'partial',
        })
        source_tx = self._create_transaction('direct', state='authorized')

        wizard = self.env['payment.capture.wizard'].create({
            'transaction_ids': source_tx.ids,
        })
        wizard.amount_to_capture = 511.11
        wizard.action_capture()

        child_tx_1 = source_tx.child_transaction_ids
        self.assertEqual(child_tx_1.state, 'draft')
        child_tx_1._set_done()

        self.env['payment.capture.wizard'].create({
            'transaction_ids': source_tx.ids,
        }).action_capture()

        child_tx_2 = (source_tx.child_transaction_ids - child_tx_1).ensure_one()
        child_tx_2._set_done()
        self.assertAlmostEqual(
            sum(source_tx.child_transaction_ids.mapped('amount')),
            source_tx.amount,
        )
        self.assertEqual(source_tx.state, 'done')

    def test_support_partial_capture_computation_with_brands(self):
        self.provider.update({
            'capture_manually': True,
            'support_manual_capture': 'partial',
        })
        dummy_brand = self.env['payment.method'].create({
            'name': "Dummy Brand",
            'code': 'dumbrand',
            'primary_payment_method_id': self.payment_method.id,
            'provider_ids': self.provider.ids,
        })
        source_tx = self._create_transaction(
            'direct', state='authorized', payment_method_id=dummy_brand.id,
        )
        wizard = self.env['payment.capture.wizard'].create({
            'transaction_ids': source_tx.ids,
        })
        self.assertTrue(wizard.support_partial_capture)
