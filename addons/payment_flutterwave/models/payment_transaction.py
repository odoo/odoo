# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_flutterwave.controllers.main import FlutterwaveController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Flutterwave-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'flutterwave':
            return res

        # Initiate the payment and retrieve the payment link data
        base_url = self.acquirer_id.get_base_url()
        payload = {
            'tx_ref': self.reference,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'payment_options': 'card',  # TODO add all payment methods
            'redirect_url': urls.url_join(base_url, FlutterwaveController._return_url),
            'customer': {
                'email': self.partner_email,
                'phonenumber': self.partner_phone,
                'name': self.partner_name,
            },
            'customizations': {
                'title': self.company_id.name,
                'logo': urls.url_join(base_url, f'web/image/res.company/{self.company_id.id}/logo'),
            },
        }
        # payload['integrity_hash'] = None  # TODO
        payment_link_data = self.acquirer_id._flutterwave_make_request('payments', payload=payload)

        # Extract the payment link URL and embed it in the redirect form
        rendering_values = {
            'api_url': payment_link_data['data']['link'],
        }
        return rendering_values

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Override of payment to find the transaction based on Flutterwave data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider, notification_data)
        if provider != 'flutterwave' or len(tx) == 1:
            return tx

        reference = notification_data.get('tx_ref')
        if not reference:
            raise ValidationError("Flutterwave: " + _("Received data with missing reference"))

        tx = self.search([('reference', '=', reference), ('provider', '=', 'flutterwave')])
        if not tx:
            raise ValidationError(
                "Flutterwave: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Flutterwave data.

        Note: self.ensure_one()

        :param dict notification_data: TODO
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider != 'flutterwave':
            return

        self.acquirer_reference = notification_data.get('transaction_id')

        # TODO verif request
        payment_status = notification_data.get('status')
        self._set_done()
