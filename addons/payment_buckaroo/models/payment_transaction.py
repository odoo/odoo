# -*- coding: utf-'8' "-*-"
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


def normalize_keys_upper(data):
    """Set all keys of a dictionnary to uppercase

    Buckaroo parameters names are case insensitive
    convert everything to upper case to be able to easily detected the presence
    of a parameter by checking the uppercase key only
    """
    return {key.upper(): value for key, value in data.iteritems()}


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # buckaroo status
    _buckaroo_valid_tx_status = [190]
    _buckaroo_pending_tx_status = [790, 791, 792, 793]
    _buckaroo_cancel_tx_status = [890, 891]
    _buckaroo_error_tx_status = [490, 491, 492]
    _buckaroo_reject_tx_status = [690]

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _buckaroo_form_get_tx_from_data(self, data):
        """ Given a data dict coming from buckaroo, verify it and find the related
        transaction record. """
        origin_data = dict(data)
        data = normalize_keys_upper(data)
        reference, pay_id, shasign = data.get('BRQ_INVOICENUMBER'), data.get('BRQ_PAYMENT'), data.get('BRQ_SIGNATURE')
        if not reference or not pay_id or not shasign:
            error_msg = _('Buckaroo: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        if len(tx) != 1:
            error_msg = _('Buckaroo: received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        #verify shasign
        shasign_check = tx.acquirer_id._buckaroo_generate_digital_sign('out', origin_data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Buckaroo: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    @api.cr_uid_records_context
    def _buckaroo_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        return tx._buckaroo_form_get_invalid_parameters(data)

    @api.v8
    def _buckaroo_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        data = normalize_keys_upper(data)
        if self.acquirer_reference and data.get('BRQ_TRANSACTIONS') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('BRQ_TRANSACTIONS'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('BRQ_AMOUNT', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('BRQ_AMOUNT'), '%.2f' % self.amount))
        if data.get('BRQ_CURRENCY') != self.currency_id.name:
            invalid_parameters.append(('Currency', data.get('BRQ_CURRENCY'), self.currency_id.name))

        return invalid_parameters

    @api.cr_uid_records_context
    def _buckaroo_form_validate(self, cr, uid, tx, data, context=None):
        return tx._buckaroo_form_validate(data)

    @api.v8
    def _buckaroo_form_validate(self, data):
        data = normalize_keys_upper(data)
        status_code = int(data.get('BRQ_STATUSCODE', '0'))
        if status_code in self._buckaroo_valid_tx_status:
            self.write({
                'state': 'done',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        elif status_code in self._buckaroo_pending_tx_status:
            self.write({
                'state': 'pending',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        elif status_code in self._buckaroo_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        else:
            error = 'Buckaroo: feedback error'
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return False
