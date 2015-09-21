# -*- coding: utf-'8' "-*-"
from hashlib import sha1
import logging
import urlparse

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_buckaroo.controllers.main import BuckarooController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class AcquirerBuckaroo(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_buckaroo_urls(self, cr, uid, environment, context=None):
        """ Buckaroo URLs
        """
        if environment == 'prod':
            return {
                'buckaroo_form_url': 'https://checkout.buckaroo.nl/html/',
            }
        else:
            return {
                'buckaroo_form_url': 'https://testcheckout.buckaroo.nl/html/',
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerBuckaroo, self)._get_providers(cr, uid, context=context)
        providers.append(['buckaroo', 'Buckaroo'])
        return providers

    _columns = {
        'brq_websitekey': fields.char('WebsiteKey', required_if_provider='buckaroo'),
        'brq_secretkey': fields.char('SecretKey', required_if_provider='buckaroo'),
    }

    def _buckaroo_generate_digital_sign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (openerp contacting buckaroo) or 'out' (buckaroo
                             contacting openerp).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.provider == 'buckaroo'

        keys = "add_returndata Brq_amount Brq_culture Brq_currency Brq_invoicenumber Brq_return Brq_returncancel Brq_returnerror Brq_returnreject brq_test Brq_websitekey".split()

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        values = dict(values or {})

        if inout == 'out':
            if 'BRQ_SIGNATURE' in values:
                del values['BRQ_SIGNATURE']
            items = sorted((k.upper(), v) for k, v in values.items())
            sign = ''.join('%s=%s' % (k, v) for k, v in items)
        else:
            sign = ''.join('%s=%s' % (k,get_value(k)) for k in keys)
        #Add the pre-shared secret key at the end of the signature
        sign = sign + acquirer.brq_secretkey
        if isinstance(sign, str):
            sign = urlparse.parse_qsl(sign)
        shasign = sha1(sign).hexdigest()
        return shasign


    def buckaroo_form_generate_values(self, cr, uid, id, values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        buckaroo_tx_values = dict(values)
        buckaroo_tx_values.update({
            'Brq_websitekey': acquirer.brq_websitekey,
            'Brq_amount': values['amount'],
            'Brq_currency': values['currency'] and values['currency'].name or '',
            'Brq_invoicenumber': values['reference'],
            'brq_test': False if acquirer.environment == 'prod' else True,
            'Brq_return': '%s' % urlparse.urljoin(base_url, BuckarooController._return_url),
            'Brq_returncancel': '%s' % urlparse.urljoin(base_url, BuckarooController._cancel_url),
            'Brq_returnerror': '%s' % urlparse.urljoin(base_url, BuckarooController._exception_url),
            'Brq_returnreject': '%s' % urlparse.urljoin(base_url, BuckarooController._reject_url),
            'Brq_culture': (values.get('partner_lang') or 'en_US').replace('_', '-'),
            'add_returndata': {'return_url': '%s' % buckaroo_tx_values.pop('return_url')} if buckaroo_tx_values.get('return_url') else ''
        })
        buckaroo_tx_values['Brq_signature'] = self._buckaroo_generate_digital_sign(acquirer, 'in', buckaroo_tx_values)
        return buckaroo_tx_values

    def buckaroo_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_buckaroo_urls(cr, uid, acquirer.environment, context=context)['buckaroo_form_url']

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
        shasign_check = self.pool['payment.acquirer']._buckaroo_generate_digital_sign(tx.acquirer_id, 'out' ,data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Buckaroo: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx 

    def _buckaroo_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        if tx.acquirer_reference and data.get('BRQ_TRANSACTIONS') != tx.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('BRQ_TRANSACTIONS'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('BRQ_AMOUNT', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('BRQ_AMOUNT'), '%.2f' % tx.amount))
        if data.get('BRQ_CURRENCY') != tx.currency_id.name:
            invalid_parameters.append(('Currency', data.get('BRQ_CURRENCY'), tx.currency_id.name))

        return invalid_parameters

    def _buckaroo_form_validate(self, cr, uid, tx, data, context=None):
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
