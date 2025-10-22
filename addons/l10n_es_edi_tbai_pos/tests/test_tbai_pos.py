from unittest.mock import patch

from odoo.addons.l10n_es_edi_tbai.tests.common import TestEsEdiTbaiCommonGipuzkoa
from odoo.addons.l10n_es_edi_tbai_pos.tests.common import CommonPosEsEdiTest
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosEdi(TestEsEdiTbaiCommonGipuzkoa, CommonPosEsEdiTest):
    @classmethod
    def pay_pos_order(self, pos_order, with_error=False):
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
        })
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=None if with_error else self.mock_response_post_invoice_success,
            side_effect=self.mock_request_error if with_error else None,
        ):
            pos_make_payment.with_context(context_make_payment).check()

    def test_tbai_pos_order(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order)
        self.assertEqual(order.state, 'paid')
        self.assertEqual(order.l10n_es_tbai_state, 'sent')

    def test_tbai_pos_order_to_invoice(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 500
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })

        # The amount is above 400 (default simplified invoice limit) so an error should be raised if it's not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(order)

        order.partner_id = self.partner_lowe
        order.to_invoice = True
        self.pay_pos_order(order)

        self.assertTrue(order.account_move)
        # The edi is handled by the invoice
        self.assertFalse(order.l10n_es_tbai_state)

    def test_tbai_refund_pos_order(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order)

        # Create the refund
        refund_action = order.refund()
        pos_refund = self.env['pos.order'].browse(refund_action['res_id'])

        # An error is raised if the refund is invoiced
        pos_refund.to_invoice = True
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund not invoiced
        pos_refund.to_invoice = False
        self.pay_pos_order(pos_refund)

        self.assertEqual(pos_refund.state, 'paid')
        self.assertEqual(pos_refund.l10n_es_tbai_state, 'sent')

    def test_tbai_refund_invoiced_pos_order(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_lowe.id,
                'to_invoice': True,
            },
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order)
        refund_action = order.refund()
        pos_refund = self.env['pos.order'].browse(refund_action['res_id'])

        # An error is raised if the refund is not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund invoiced
        pos_refund.to_invoice = True
        self.pay_pos_order(pos_refund)
        self.assertTrue(pos_refund.account_move)
        self.assertFalse(pos_refund.l10n_es_tbai_state)

    def test_tbai_pos_order_with_failed_chain_head(self):
        self.ten_dollars_with_10_incl.product_variant_id.lst_price = 100
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order, with_error=True)
        self.assertNotEqual(order.l10n_es_tbai_state, 'sent')

        order2, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id}
            ],
        })
        self.pay_pos_order(order2)

        # the second order should retry the unposted chain head
        self.assertEqual(order.l10n_es_tbai_state, 'sent')
        self.assertEqual(order2.l10n_es_tbai_state, 'sent')
