# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging
import pprint

_logger = logging.getLogger(__name__)


class CustomPaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('custom', 'Custom')])

    def transfer_get_form_action_url(self):
        return '/payment/custom/feedback'


class TransferPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _custom_form_get_tx_from_data(self, data):
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

    def _custom_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))

        return invalid_parameters

    def _custom_form_validate(self, data):
        _logger.info('Validated custom payment for tx %s: set as pending' % (self.reference))
        return self.write({'state': 'pending'})
