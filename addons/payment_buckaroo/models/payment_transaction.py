# -*- coding: utf-'8' "-*-"
import logging

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.osv import osv
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


def normalize_keys_upper(data):
    """Set all keys of a dictionnary to uppercase

    Buckaroo parameters names are case insensitive
    convert everything to upper case to be able to easily detected the presence
    of a parameter by checking the uppercase key only
    """
    return dict((key.upper(), val) for key, val in data.items())


class TxBuckaroo(osv.Model):
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

    def _buckaroo_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from buckaroo, verify it and find the related
        transaction record. """
        origin_data = dict(data)
        data = normalize_keys_upper(data)
        reference, pay_id, shasign = data.get('BRQ_INVOICENUMBER'), data.get('BRQ_PAYMENT'), data.get('BRQ_SIGNATURE')
        if not reference or not pay_id or not shasign:
            error_msg = _('Buckaroo: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        tx_ids = self.search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = _('Buckaroo: received data for reference %s') % (reference)
            if not tx_ids:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        #verify shasign
        shasign_check = self.pool['payment.acquirer']._buckaroo_generate_digital_sign(tx.acquirer_id, 'out', origin_data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Buckaroo: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx 

    def _buckaroo_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []
        data = normalize_keys_upper(data)
        if tx.acquirer_reference and data.get('BRQ_TRANSACTIONS') != tx.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('BRQ_TRANSACTIONS'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('BRQ_AMOUNT', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('BRQ_AMOUNT'), '%.2f' % tx.amount))
        if data.get('BRQ_CURRENCY') != tx.currency_id.name:
            invalid_parameters.append(('Currency', data.get('BRQ_CURRENCY'), tx.currency_id.name))

        return invalid_parameters

    def _buckaroo_form_validate(self, cr, uid, tx, data, context=None):
        data = normalize_keys_upper(data)
        status_code = int(data.get('BRQ_STATUSCODE','0'))
        if status_code in self._buckaroo_valid_tx_status:
            tx.write({
                'state': 'done',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        elif status_code in self._buckaroo_pending_tx_status:
            tx.write({
                'state': 'pending',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        elif status_code in self._buckaroo_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return True
        else:
            error = 'Buckaroo: feedback error'
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('BRQ_TRANSACTIONS'),
            })
            return False
