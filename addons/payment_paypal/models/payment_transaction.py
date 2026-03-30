# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_paypal.const import PAYMENT_STATUS_MAPPING
from odoo.addons.payment_paypal.controllers.main import PaypalController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNandPDTVariables/
    # this field has no use in Odoo except for debugging
    paypal_type = fields.Char(string="PayPal Transaction Type")

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Paypal-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'paypal':
            return res

        base_url = self.provider_id.get_base_url()
        partner_first_name, partner_last_name = payment_utils.split_partner_name(self.partner_name)
        webhook_url = urls.url_join(base_url, PaypalController._webhook_url)
        if (
            self.partner_address
            and self.partner_city
            and self.partner_country_id
            and (self.partner_zip or not self.partner_country_id.zip_required)
            and (self.partner_state_id or not self.partner_country_id.state_required)
        ):
            # Ensure given address cannot be altered.
            no_shipping = '0'
            address_override = '1'
        else:
            # Do not prompt for a delivery address.
            no_shipping = '1'
            address_override = '0'
        return {
            'address1': self.partner_address,
            'amount': self.amount,
            'business': self.provider_id.paypal_email_account,
            'city': self.partner_city,
            'country': self.partner_country_id.code,
            'currency_code': self.currency_id.name,
            'email': self.partner_email,
            'first_name': partner_first_name,
            'handling': self.fees,
            'item_name': f"{self.company_id.name}: {self.reference}",
            'item_number': self.reference,
            'last_name': partner_last_name,
            'lc': self.partner_lang,
            'no_shipping': no_shipping,
            'address_override': address_override,
            'notify_url': webhook_url if self.provider_id.paypal_use_ipn else None,
            'return_url': urls.url_join(base_url, PaypalController._return_url),
            'state': self.partner_state_id.name,
            'zip_code': self.partner_zip,
            'api_url': self.provider_id._paypal_get_api_url(),
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Paypal data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'paypal' or len(tx) == 1:
            return tx

        reference = notification_data.get('item_number')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'paypal')])
        if not tx:
            raise ValidationError(
                "PayPal: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Paypal data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'paypal':
            return

        amount = notification_data.get('amt') or notification_data.get('mc_gross')
        currency_code = notification_data.get('cc') or notification_data.get('mc_currency')
        assert amount and currency_code, 'PayPal: missing amount or currency'
        assert self.currency_id.compare_amounts(float(amount), self.amount + self.fees) == 0, \
            'PayPal: mismatching amounts'
        assert currency_code == self.currency_id.name, 'PayPal: mismatching currency codes'

        txn_id = notification_data.get('txn_id')
        txn_type = notification_data.get('txn_type')
        if not all((txn_id, txn_type)):
            raise ValidationError(
                "PayPal: " + _(
                    "Missing value for txn_id (%(txn_id)s) or txn_type (%(txn_type)s).",
                    txn_id=txn_id, txn_type=txn_type
                )
            )
        self.provider_reference = txn_id
        self.paypal_type = txn_type

        payment_status = notification_data.get('payment_status')

        if payment_status in PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending(state_message=notification_data.get('pending_reason'))
        elif payment_status in PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        else:
            _logger.info(
                "received data with invalid payment status (%s) for transaction with reference %s",
                payment_status, self.reference
            )
            self._set_error(
                "PayPal: " + _("Received data with invalid payment status: %s", payment_status)
            )
