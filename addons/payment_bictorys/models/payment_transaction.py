# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_bictorys.const import PAYMENT_STATUS_MAPPING

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Bictorys-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        :raise ValidationError: If the API request fails.
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'bictorys':
            return res

        base_url = self.provider_id.get_base_url()
        payload = self._bictorys_prepare_charge_payload(base_url)

        _logger.info(
            "Sending 'charges' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload),
        )
        charge_data = self.provider_id._bictorys_make_request('pay/v1/charges', payload=payload)
        _logger.info(
            "Response of 'charges' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(charge_data),
        )

        return {
            'api_url': charge_data.get('link'),
            'charge_id': charge_data.get('chargeId'),
            'op_token': charge_data.get('opToken'),
        }

    def _bictorys_prepare_charge_payload(self, base_url):
        """ Prepare the payload for the Bictorys charge creation request.

        :param str base_url: The base URL of the Odoo instance.
        :return: The payload to create a Bictorys charge.
        :rtype: dict
        """
        return {
            'amount': self.amount,
            'currency': self.currency_id.name,
            'customerObject': {
                'name': self.partner_name,
                'email': self.partner_email or '',
                'phone': self.partner_phone or '',
            },
            'paymentReference': self.reference,
            'successRedirectUrl': f'{base_url}/payment/bictorys/return?ref={self.reference}&status=success',
            'errorRedirectUrl': f'{base_url}/payment/bictorys/return?ref={self.reference}&status=cancel',
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Bictorys data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'bictorys' or len(tx) == 1:
            return tx

        reference = notification_data.get('paymentReference') or notification_data.get('ref')
        if not reference:
            raise ValidationError(
                "Bictorys: " + _("Missing payment reference in the notification data.")
            )
        tx = self.search(
            [('reference', '=', reference), ('provider_code', '=', 'bictorys')]
        )
        if not tx:
            raise ValidationError(
                "Bictorys: " + _(
                    "No transaction found matching reference %s.", reference
                )
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Bictorys data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'bictorys':
            return

        # Handle explicit cancellation (user left the payment page).
        if notification_data.get('status') == 'cancel':
            self._set_canceled(state_message=_("The customer left the payment page."))
            return

        # Verify the transaction via the Bictorys API.
        _logger.info(
            "Verifying transaction with reference %s via Bictorys API.", self.reference
        )
        verification = self.provider_id._bictorys_make_request(
            f'pay/v1/transactions/verify_by_reference?tx_ref={self.reference}',
            method='GET',
        )
        data = verification.get('data', verification)

        # Update the provider reference.
        provider_reference = data.get('id') or notification_data.get('id')
        if provider_reference:
            self.provider_reference = str(provider_reference)

        # Update the payment method if provided.
        payment_type = data.get('payment_type', '')
        if payment_type:
            payment_method = self.env['payment.method'].search(
                [('code', '=', payment_type.lower())], limit=1
            )
            self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = (data.get('status') or notification_data.get('status', '')).lower()
        if not payment_status:
            raise ValidationError(
                "Bictorys: " + _("Missing payment status in the notification data.")
            )

        if payment_status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in PAYMENT_STATUS_MAPPING['error']:
            self._set_error(
                "Bictorys: " + _("Payment failed with status: %s", payment_status)
            )
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s",
                payment_status, self.reference,
            )
            self._set_error(
                "Bictorys: " + _("Received data with invalid payment status: %s", payment_status)
            )

    def _get_processing_values(self):
        """ Prepare the payment processing values including redirect form for Bictorys. """
        self.ensure_one()

        processing_values = {
            'provider_id': self.provider_id.id,
            'provider_code': self.provider_code,
            'reference': self.reference,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
        }

        # Get the provider-specific rendering values.
        processing_values.update(self._get_specific_rendering_values(processing_values))

        # Build the redirect form if needed.
        if self.operation in ('online_redirect', 'validation') and self.provider_code == 'bictorys':
            redirect_form_view = self.env.ref('payment_bictorys.redirect_form_bictorys')
            if redirect_form_view:
                redirect_form_html = self.env['ir.qweb']._render(
                    redirect_form_view.id,
                    processing_values,
                )
                processing_values.update(redirect_form_html=redirect_form_html)

        return processing_values