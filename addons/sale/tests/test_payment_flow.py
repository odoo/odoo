# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import ANY, patch

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('-at_install', 'post_install')
class TestSalePayment(AccountPaymentCommon, SaleCommon, PaymentHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Replace PaymentCommon defaults by SaleCommon ones
        cls.currency = cls.sale_order.currency_id
        cls.partner = cls.sale_order.partner_id

    def test_11_so_payment_link(self):
        # test customized /payment/pay route with sale_order_id param
        self.amount = self.sale_order.amount_total
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.sale_order.id

        with patch(
            'odoo.addons.payment.controllers.portal.PaymentPortal'
            '._compute_show_tokenize_input_mapping'
        ) as patched:
            tx_context = self._get_tx_checkout_context(**route_values)
            patched.assert_called_once_with(ANY, logged_in=ANY, sale_order_id=ANY)

        self.assertEqual(tx_context['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_id.id)
        self.assertEqual(tx_context['amount'], self.sale_order.amount_total)
        self.assertEqual(tx_context['sale_order_id'], self.sale_order.id)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.provider.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': None, # Force empty prefix to fallback on SO reference
            'landing_route': tx_context['landing_route'],
            'amount': tx_context['amount'],
            'currency_id': tx_context['currency_id'],
        })

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx_sudo.sale_order_ids, self.sale_order)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.partner_id, self.sale_order.partner_id)
        self.assertEqual(tx_sudo.company_id, self.sale_order.company_id)
        self.assertEqual(tx_sudo.currency_id, self.sale_order.currency_id)
        self.assertEqual(tx_sudo.reference, self.sale_order.name)

        # Check validation of transaction correctly confirms the SO
        self.assertEqual(self.sale_order.state, 'draft')
        self.assertEqual(tx_sudo.sale_order_ids.transaction_ids, tx_sudo)
        tx_sudo._set_done()
        tx_sudo._finalize_post_processing()
        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(tx_sudo.payment_id)
        self.assertEqual(tx_sudo.payment_id.state, 'posted')

    def test_12_so_partial_payment_link(self):
        # test customized /payment/pay route with sale_order_id param
        # partial amount specified
        self.amount = self.sale_order.amount_total / 2.0
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_tx_checkout_context(**route_values)

        self.assertEqual(tx_context['reference_prefix'], self.reference)
        self.assertEqual(tx_context['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_id.id)
        self.assertEqual(tx_context['amount'], self.amount)
        self.assertEqual(tx_context['sale_order_id'], self.sale_order.id)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.provider.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx_sudo.sale_order_ids, self.sale_order)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.partner_id, self.sale_order.partner_id)
        self.assertEqual(tx_sudo.company_id, self.sale_order.company_id)
        self.assertEqual(tx_sudo.currency_id, self.sale_order.currency_id)
        self.assertEqual(tx_sudo.reference, self.reference)
        self.assertEqual(tx_sudo.sale_order_ids.transaction_ids, tx_sudo)

        tx_sudo._set_done()
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx_sudo._finalize_post_processing()
        self.assertEqual(self.sale_order.state, 'draft') # Only a partial amount was paid

        # Pay the remaining amount
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_tx_checkout_context(**route_values)

        self.assertEqual(tx_context['reference_prefix'], self.reference)
        self.assertEqual(tx_context['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_id.id)
        self.assertEqual(tx_context['amount'], self.amount)
        self.assertEqual(tx_context['sale_order_id'], self.sale_order.id)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.provider.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(**route_values)
        tx2_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx2_sudo.sale_order_ids, self.sale_order)
        self.assertEqual(tx2_sudo.amount, self.amount)
        self.assertEqual(tx2_sudo.partner_id, self.sale_order.partner_id)
        self.assertEqual(tx2_sudo.company_id, self.sale_order.company_id)
        self.assertEqual(tx2_sudo.currency_id, self.sale_order.currency_id)

        # We are paying a second time with the same reference (prefix)
        # a suffix is added to respect unique reference constraint
        reference = self.reference + "-1"
        self.assertEqual(tx2_sudo.reference, reference)
        self.assertEqual(self.sale_order.state, 'draft')
        self.assertEqual(self.sale_order.transaction_ids, tx_sudo + tx2_sudo)

    def test_13_sale_automatic_partial_payment_link_delivery(self):
        """Test that with automatic invoice and invoicing policy based on delivered quantity, a transaction for the partial
        amount does not validate the SO."""
        # set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        # invoicing policy is based on delivered quantity
        self.product.invoice_policy = 'delivery'

        self.amount = self.sale_order.amount_total / 2.0
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_tx_checkout_context(**route_values)

        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.provider.id,
            'tokenization_requested': False,
            'validation_route': False,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        tx_sudo._set_done()
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx_sudo._finalize_post_processing()

        self.assertEqual(self.sale_order.state, 'draft', 'a partial transaction with automatic invoice and invoice_policy = delivery should not validate a quote')

    def test_confirmed_transactions_comfirms_so_with_multiple_transaction(self):
        """ Test that a confirmed transaction confirms a SO even if one or more non-confirmed
        transactions are linked. """
        # Create the payment
        self.amount = self.sale_order.amount_total
        self._create_transaction(
            flow='redirect',
            sale_order_ids=[self.sale_order.id],
            state='draft',
            reference='Test Transaction Draft 1',
        )
        self._create_transaction(
            flow='redirect',
            sale_order_ids=[self.sale_order.id],
            state='draft',
            reference='Test Transaction Draft 2',
        )
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        tx._reconcile_after_done()

        self.assertEqual(self.sale_order.state, 'sale')

    def test_auto_confirm_and_auto_invoice(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()

        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)

    def test_auto_done_and_auto_invoice(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        # Lock the sale orders when confirmed
        self.env.user.groups_id += self.env.ref('sale.group_auto_done_setting')

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()

        self.assertEqual(self.sale_order.state, 'done')
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)

    def test_so_partial_payment_no_invoice(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create the payment
        self.amount = self.sale_order.amount_total / 10.
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()

        self.assertEqual(self.sale_order.state, 'draft')
        self.assertFalse(tx.invoice_ids)
        self.assertFalse(self.sale_order.invoice_ids)

    def test_already_confirmed_so_payment(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Confirm order before payment
        self.sale_order.action_confirm()

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        tx._reconcile_after_done()

        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)
