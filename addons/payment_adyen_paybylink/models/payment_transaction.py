# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def adyen_create(self, values):
        """
        When the customer lands on the `/payment/process` route, `/payment/process/poll` try to find
        the transaction whose `date` field is between yesterday and now.

        Since the `date` field is only set when the state of the transaction is changed, if the
        customer comes back before the webhook, he will see a "transaction not found" page because
        the value of the `date` field would be `False`.
        """
        return dict(date=fields.Datetime.now())

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _adyen_form_get_tx_from_data(self, data):
        """ Override of _adyen_form_get_tx_from_data """
        reference, psp_reference = data.get('merchantReference'), data.get('pspReference')
        if not reference or not psp_reference:
            error_msg = _(
                "Adyen: received data with missing reference (%s) or missing pspReference (%s)"
            ) % (reference, psp_reference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        tx = self.env['payment.transaction'].search([
            ('reference', '=', reference), ('provider', '=', 'adyen')
        ])
        if not tx or len(tx) > 1:
            error_msg = _("Adyen: received data for reference %s") % reference
            if not tx:
                error_msg += _("; no order found")
            else:
                error_msg += _("; multiple order found")
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _adyen_form_get_invalid_parameters(self, data):
        """ Override of _adyen_form_get_invalid_parameters to disable this method.

        The pay-by-link implementation doesn't need or want to check for invalid parameters.
        """
        return []
