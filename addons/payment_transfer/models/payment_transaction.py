# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging
import pprint

_logger = logging.getLogger(__name__)


class TransferPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _get_tx_from_data(self, provider, data):
        if provider != "transfer":
            return super()._get_tx_from_data(provider, data)

        reference = data.get('reference')
        tx = self.search([('reference', '=', reference)])

        if not tx or len(tx) > 1:
            error_msg = _('received data for reference %s') % (pprint.pformat(reference))
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx

    def _get_specific_rendering_values(self, processing_values):
        self.ensure_one()
        if self.provider != "transfer":
            return super()._get_specific_rendering_values(processing_values)

        return {
            'currency': self.currency_id.name,
            'tx_url': self.acquirer_id._transfer_get_redirect_action_url(),
            **processing_values,
        }

    def _get_invalid_parameters(self, data):
        if self.provider != "transfer":
            return super()._get_invalid_parameters(data)

        invalid_parameters = []

        if float_compare(float(data.get('amount') or '0.0'), self.amount, 2) != 0:
            invalid_parameters['amount'] = (data.get('amount'), '%.2f' % self.amount)
        if data.get('currency') != self.currency_id.name:
            invalid_parameters['currency'] = (data.get('currency'), self.currency_id.name)

        return invalid_parameters

    def _process_feedback_data(self, data):
        if self.provider != "transfer":
            return super()._process_feedback_data(data)

        _logger.info('Validated transfer payment for tx %s: set as pending' % (self.reference))
        self._set_pending()

        return True
