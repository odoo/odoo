# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import ANY, patch

from odoo.fields import Command
from odoo.tests import tagged, JsonRpcException
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
        cls.partner = cls.sale_order.partner_invoice_id

    def test_11_so_payment_link(self):
        # test customized /payment/pay route with sale_order_id param
        self.amount = self.sale_order.amount_total
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.sale_order.id

        with patch(
            'odoo.addons.payment.controllers.portal.PaymentPortal'
            '._compute_show_tokenize_input_mapping'
        ) as patched:
            tx_context = self._get_portal_pay_context(**route_values)
            patched.assert_called_once_with(ANY, sale_order_id=ANY)

        self.assertEqual(tx_context['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_invoice_id.id)
        self.assertEqual(tx_context['amount'], self.sale_order.amount_total)

        # /my/orders/<id>/transaction/
        tx_route_values = {
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'amount': tx_context['amount'],
            'flow': 'direct',
            'tokenization_requested': False,
            'landing_route': tx_context['landing_route'],
            'access_token': tx_context['access_token'],
        }
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(
                tx_route=tx_context['transaction_route'], **tx_route_values
            )
        tx_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx_sudo.sale_order_ids, self.sale_order)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.partner_id, self.sale_order.partner_invoice_id)
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

    def test_so_payment_link_with_different_partner_invoice(self):
        # test customized /payment/pay route with sale_order_id param
        # partner_id and partner_invoice_id different on the so
        self.sale_order.partner_invoice_id = self.portal_partner
        self.partner = self.sale_order.partner_invoice_id
        route_values = self._prepare_pay_values()
        route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_portal_pay_context(**route_values)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_invoice_id.id)

    def test_12_so_partial_payment_link(self):
        # test customized /payment/pay route with sale_order_id param
        # partial amount specified
        self.amount = self.sale_order.amount_total / 2.0
        pay_route_values = self._prepare_pay_values()
        pay_route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_portal_pay_context(**pay_route_values)

        self.assertEqual(tx_context['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_invoice_id.id)
        self.assertEqual(tx_context['amount'], self.amount)

        tx_route_values = {
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'amount': tx_context['amount'],
            'flow': 'direct',
            'tokenization_requested': False,
            'landing_route': tx_context['landing_route'],
            'access_token': tx_context['access_token'],
        }
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(
                tx_route=tx_context['transaction_route'], **tx_route_values
            )
        tx_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx_sudo.sale_order_ids, self.sale_order)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.partner_id, self.sale_order.partner_invoice_id)
        self.assertEqual(tx_sudo.company_id, self.sale_order.company_id)
        self.assertEqual(tx_sudo.currency_id, self.sale_order.currency_id)
        self.assertEqual(tx_sudo.sale_order_ids.transaction_ids, tx_sudo)

        tx_sudo._set_done()
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx_sudo._finalize_post_processing()
        self.assertEqual(self.sale_order.state, 'draft') # Only a partial amount was paid

        # Pay the remaining amount
        pay_route_values = self._prepare_pay_values()
        pay_route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_portal_pay_context(**pay_route_values)

        self.assertEqual(tx_context['currency_id'], self.sale_order.currency_id.id)
        self.assertEqual(tx_context['partner_id'], self.sale_order.partner_invoice_id.id)
        self.assertEqual(tx_context['amount'], self.amount)

        tx_route_values = {
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'amount': tx_context['amount'],
            'flow': 'direct',
            'tokenization_requested': False,
            'landing_route': tx_context['landing_route'],
            'access_token': tx_context['access_token'],
        }
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(
                tx_route=tx_context['transaction_route'], **tx_route_values
            )
        tx2_sudo = self._get_tx(processing_values['reference'])

        self.assertEqual(tx2_sudo.sale_order_ids, self.sale_order)
        self.assertEqual(tx2_sudo.amount, self.amount)
        self.assertEqual(tx2_sudo.partner_id, self.sale_order.partner_invoice_id)
        self.assertEqual(tx2_sudo.company_id, self.sale_order.company_id)
        self.assertEqual(tx2_sudo.currency_id, self.sale_order.currency_id)

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
        pay_route_values = self._prepare_pay_values()
        pay_route_values['sale_order_id'] = self.sale_order.id

        tx_context = self._get_portal_pay_context(**pay_route_values)

        tx_route_values = {
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method_id,
            'token_id': None,
            'amount': tx_context['amount'],
            'flow': 'direct',
            'tokenization_requested': False,
            'landing_route': tx_context['landing_route'],
            'access_token': tx_context['access_token'],
        }
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self._get_processing_values(
                tx_route=tx_context['transaction_route'], **tx_route_values
            )
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

        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(self.sale_order.locked)
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)
        self.assertTrue(tx.invoice_ids.is_move_sent)

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

    def test_invoice_is_final(self):
        """Test that invoice generated from a payment are always final"""
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(
            flow='redirect',
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'), patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._create_invoices',
            return_value=self.env['account.move']
        ) as _create_invoices_mock:
            tx._reconcile_after_done()

        self.assertTrue(_create_invoices_mock.call_args.kwargs['final'])

    def test_downpayment_confirm_sale_order_sufficient_amount(self):
        """Paying down payments can confirm an order if amount is enough."""
        self.sale_order.require_payment = True
        self.sale_order.prepayment_percent = 0.1
        order_amount = self.sale_order.amount_total

        tx = self._create_transaction(
            flow='direct',
            amount=order_amount * self.sale_order.prepayment_percent,
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()

        self.assertTrue(self.sale_order.state == 'sale')

    def test_downpayment_confirm_sale_order_insufficient_amount(self):
        """Confirmation cannot occur if amount is not enough."""

        self.sale_order.require_payment = True
        self.sale_order.prepayment_percent = 0.2
        order_amount = self.sale_order.amount_total

        tx = self._create_transaction(
            flow='direct',
            amount=order_amount * 0.10,
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()

        self.assertTrue(self.sale_order.state == 'draft')

    def test_downpayment_confirm_sale_order_several_payments(self):
        """
        Several payments also trigger the confirmation of the sale order if
        down payment confirmation is allowed.
        """
        self.sale_order.require_payment = True
        self.sale_order.prepayment_percent = 0.2
        order_amount = self.sale_order.amount_total

        # Make a first payment, order should not be confirmed.
        tx = self._create_transaction(
            flow='direct',
            reference="Test down payment 1",
            amount=order_amount * 0.1,
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        tx._reconcile_after_done()
        self.assertTrue(self.sale_order.state == 'draft')

        # Order should be confirmed after this payment.
        tx = self._create_transaction(
            flow='direct',
            reference="Test down payment 2",
            amount=order_amount * 0.15,
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        tx._reconcile_after_done()
        self.assertTrue(self.sale_order.state == 'sale')

    def test_downpayment_automatic_invoice(self):
        """
        Down payment invoices should be created when a down payment confirms
        the order and automatic invoice is checked.
        """
        self.sale_order.require_payment = True
        self.sale_order.prepayment_percent = 0.2
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        tx = self._create_transaction(
            flow='direct',
            amount=self.sale_order.amount_total * self.sale_order.prepayment_percent,
            sale_order_ids=[self.sale_order.id],
            state='done')

        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._reconcile_after_done()

        invoice = self.sale_order.invoice_ids
        self.assertTrue(len(invoice) == 1)
        self.assertTrue(invoice.line_ids[0].is_downpayment)

    @mute_logger('odoo.http')
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f'/my/orders/{self.sale_order.id}/transaction')
        route_kwargs = {
            'access_token': self.sale_order._portal_ensure_token(),
            'partner_id': self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)
