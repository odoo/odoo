# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from werkzeug import urls

from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.payment_buckaroo.const import STATUS_CODES_MAPPING
from odoo.addons.payment_buckaroo.controllers.main import BuckarooController

_logger = logging.getLogger(__name__)


def _normalize_dataset(data):
    """ Set all keys of a dictionary to uppercase.

    As Buckaroo parameters names are case insensitive, we can convert everything to upper case to
    easily detected the presence of a parameter by checking the uppercase key only.

    :param dict data: The dictionary whose keys must be set to uppercase
    :return: A copy of the original data with all keys set to uppercase
    :rtype: dict
    """
    return {key.upper(): val for key, val in data.items()}


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Buckaroo-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider != 'buckaroo':
            return res

        return_url = urls.url_join(self.acquirer_id.get_base_url(), BuckarooController._return_url)
        rendering_values = {
            'api_url': self.acquirer_id._buckaroo_get_api_url(),
            'Brq_websitekey': self.acquirer_id.buckaroo_website_key,
            'Brq_amount': self.amount,
            'Brq_currency': self.currency_id.name,
            'Brq_invoicenumber': self.reference,
            # Include all 4 URL keys despite they share the same value as they are part of the sig.
            'Brq_return': return_url,
            'Brq_returncancel': return_url,
            'Brq_returnerror': return_url,
            'Brq_returnreject': return_url,
        }
        if self.partner_lang:
            rendering_values['Brq_culture'] = self.partner_lang.replace('_', '-')
        rendering_values['Brq_signature'] = self.acquirer_id._buckaroo_generate_digital_sign(
            rendering_values, incoming=False
        )
        return rendering_values

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Buckaroo data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        :raise: ValidationError if the signature can not be verified
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'buckaroo':
            return tx

        normalized_data = _normalize_dataset(data)
        reference = normalized_data.get('BRQ_INVOICENUMBER')
        shasign = normalized_data.get('BRQ_SIGNATURE')
        if not reference or not shasign:
            raise ValidationError(
                "Buckaroo: " + _(
                    "Received data with missing reference (%(ref)s) or shasign (%(sign)s)",
                    ref=reference, sign=shasign
                )
            )

        tx = self.search([('reference', '=', reference), ('provider', '=', 'buckaroo')])
        if not tx:
            raise ValidationError(
                "Buckaroo: " + _("No transaction found matching reference %s.", reference)
            )

        # Verify signature
        shasign_check = tx.acquirer_id._buckaroo_generate_digital_sign(data, incoming=True)
        if shasign_check != shasign:
            raise ValidationError(
                "Buckaroo: " + _(
                    "Invalid shasign: received %(sign)s, computed %(check)s",
                    sign=shasign, check=shasign_check
                )
            )

        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Buckaroo data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_feedback_data(data)
        if self.provider != 'buckaroo':
            return

        normalized_data = _normalize_dataset(data)
        transaction_keys = normalized_data.get('BRQ_TRANSACTIONS')
        if not transaction_keys:
            raise ValidationError("Buckaroo: " + _("Received data with missing transaction keys"))
        # BRQ_TRANSACTIONS can hold multiple, comma-separated, tx keys. In practice, it holds only
        # one reference. So we split for semantic correctness and keep the first transaction key.
        self.acquirer_reference = transaction_keys.split(',')[0]

        status_code = int(normalized_data.get('BRQ_STATUSCODE') or 0)
        if status_code in STATUS_CODES_MAPPING['pending']:
            self._set_pending()
        elif status_code in STATUS_CODES_MAPPING['done']:
            self._set_done()
        elif status_code in STATUS_CODES_MAPPING['cancel']:
            self._set_canceled()
        elif status_code in STATUS_CODES_MAPPING['refused']:
            self._set_error(_("Your payment was refused (code %s). Please try again.", status_code))
        elif status_code in STATUS_CODES_MAPPING['error']:
            self._set_error(_("An error occurred during processing of your payment (code %s). Please try again.", status_code))
        else:
            _logger.warning("Buckaroo: received unknown status code: %s", status_code)
            self._set_error("Buckaroo: " + _("Unknown status code: %s", status_code))
