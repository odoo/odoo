# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged, JsonRpcException
from odoo.tools import mute_logger

from odoo.addons.account_payment.controllers.payment import PaymentPortal
from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.portal.controllers.portal import CustomerPortal


@tagged('post_install', '-at_install')
class TestFlows(AccountPaymentCommon, PaymentHttpCommon):

    def test_invoice_payment_flow(self):
        """Test the payment of an invoice through the payment/pay route"""

        # Pay for this invoice (no impact even if amounts do not match)
        route_values = self._prepare_pay_values()
        route_values['invoice_id'] = self.invoice.id
        tx_context = self._get_portal_pay_context(**route_values)

        # /invoice/transaction/<id>
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
        # Note: strangely, the check
        # self.assertEqual(tx_sudo.invoice_ids, invoice)
        # doesn't work, and cache invalidation doesn't work either.
        self.invoice.invalidate_recordset(['transaction_ids'])
        self.assertEqual(self.invoice.transaction_ids, tx_sudo)

    def test_check_portal_access_token_before_rerouting_flow(self):
        """ Test that access to the provided invoice is checked against the portal access token
        before rerouting the payment flow. """
        payment_portal_controller = PaymentPortal()

        with patch.object(CustomerPortal, '_document_check_access') as mock:
            payment_portal_controller._get_extra_payment_form_values()
            self.assertEqual(
                mock.call_count, 0, msg="No check should be made when invoice_id is not provided."
            )

            mock.reset_mock()

            payment_portal_controller._get_extra_payment_form_values(
                invoice_id=self.invoice.id, access_token='whatever'
            )
            self.assertEqual(
                mock.call_count, 1, msg="The check should be made as invoice_id is provided."
            )

    def test_check_payment_access_token_before_rerouting_flow(self):
        """ Test that access to the provided invoice is checked against the payment access token
        before rerouting the payment flow. """
        payment_portal_controller = PaymentPortal()

        def _document_check_access_mock(*_args, **_kwargs):
            raise AccessError('')

        with patch.object(
            CustomerPortal, '_document_check_access', _document_check_access_mock
        ), patch('odoo.addons.payment.utils.check_access_token') as check_payment_access_token_mock:
            try:
                payment_portal_controller._get_extra_payment_form_values(
                    invoice_id=self.invoice.id, access_token='whatever'
                )
            except Exception:
                pass  # We don't care if it runs or not; we only count the calls.
            self.assertEqual(
                check_payment_access_token_mock.call_count,
                1,
                msg="The access token should be checked again as a payment access token if the"
                    " check as a portal access token failed.",
            )

    @mute_logger('odoo.http')
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f'/invoice/transaction/{self.invoice.id}/')
        route_kwargs = {
            'access_token': self.invoice._portal_ensure_token(),
            'partner_id': self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)
