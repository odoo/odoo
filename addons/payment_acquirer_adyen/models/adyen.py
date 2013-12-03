# -*- coding: utf-'8' "-*-"

import base64
try:
    import simplejson as json
except ImportError:
    import json
from hashlib import sha1
import hmac
import logging
import urlparse

from openerp.addons.payment_acquirer.models.payment_acquirer import ValidationError
from openerp.addons.payment_acquirer_adyen.controllers.main import AdyenController
from openerp.osv import osv, fields
from openerp.tools import float_round

_logger = logging.getLogger(__name__)


class AcquirerAdyen(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_adyen_urls(self, cr, uid, ids, name, args, context=None):
        """ Adyen URLs

         - yhpp: hosted payment page: pay.shtml for single, select.shtml for multiple
        """
        res = {}
        for acquirer in self.browse(cr, uid, ids, context=context):
            qualif = acquirer.env
            res[acquirer.id] = {
                'adyen_form_url': 'https://%s.adyen.com/hpp/pay.shtml' % qualif,
            }
        return res

    _columns = {
        'adyen_merchant_account': fields.char('Merchant Account', required_if_provider='adyen'),
        'adyen_skin_code': fields.char('Skin Code', required_if_provider='adyen'),
        'adyen_skin_hmac_key': fields.char('Skin HMAC Key', required_if_provider='adyen'),
        'adyen_form_url': fields.function(
            _get_adyen_urls, multi='_get_adyen_urls',
            type='char', string='Transaction URL', required_if_provider='adyen'),
    }

    def _adyen_generate_merchant_sig(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (openerp contacting ogone) or 'out' (adyen
                             contacting openerp). In this last case only some
                             fields should be contained (see e-Commerce basic)
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.name == 'adyen'

        if inout == 'in':
            keys = "paymentAmount currencyCode shipBeforeDate merchantReference skinCode merchantAccount sessionValidity shopperEmail shopperReference recurringContract allowedMethods blockedMethods shopperStatement merchantReturnData billingAddressType deliveryAddressType offset".split()
        else:
            keys = "authResult pspReference merchantReference skinCode paymentMethod shopperLocale merchantReturnData".split()

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        sign = ''.join('%s' % get_value(k) for k in keys).encode('ascii')
        key = acquirer.adyen_skin_hmac_key.encode('ascii')
        return base64.b64encode(hmac.new(key, sign, sha1).digest())

    def adyen_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        # tmp
        import datetime
        from dateutil import relativedelta
        tmp_date = datetime.date.today() + relativedelta.relativedelta(days=1)

        adyen_tx_values = dict(tx_values)
        adyen_tx_values.update({
            'merchantReference': tx_values['reference'],
            'paymentAmount': '%d' % int(float_round(tx_values['amount'], 2) * 100),
            'currencyCode': tx_values['currency'] and tx_values['currency'].name or '',
            'shipBeforeDate': tmp_date,
            'skinCode': acquirer.adyen_skin_code,
            'merchantAccount': acquirer.adyen_merchant_account,
            'shopperLocale': partner_values['lang'],
            'sessionValidity': tmp_date,
            'resURL': '%s' % urlparse.urljoin(base_url, AdyenController._return_url),
        })
        if adyen_tx_values.get('return_url'):
            adyen_tx_values['merchantReturnData'] = json.dumps({'return_url': '%s' % adyen_tx_values.pop('return_url')})
        adyen_tx_values['merchantSig'] = self._adyen_generate_merchant_sig(acquirer, 'in', adyen_tx_values)
        return partner_values, adyen_tx_values

    def adyen_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return acquirer.adyen_form_url


class TxAdyen(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'adyen_psp_reference': fields.char('Adyen PSP Reference'),
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _adyen_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, pspReference = data.get('merchantReference'), data.get('pspReference')
        if not reference or not pspReference:
            error_msg = 'Adyen: received data with missing reference (%s) or missing pspReference (%s)' % (reference, pspReference)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use pspReference ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Adyen: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        # verify shasign
        shasign_check = self.pool['payment.acquirer']._adyen_generate_merchant_sig(tx.acquirer_id, 'out', data)
        if shasign_check != data.get('merchantSig'):
            error_msg = 'Adyen: invalid merchantSig, received %s, computed %s' % (data.get('merchantSig'), shasign_check)
            _logger.warning(error_msg)
            # raise ValidationError(error_msg)

        return tx

    def _adyen_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        invalid_parameters = []
        if data.get('skinCode') != tx.acquirer_id.adyen_skin_code:
            invalid_parameters.append(('skinCode', data.get('skinCode'), tx.acquirer_id.adyen_skin_code))
        if not data.get('authResult'):
            invalid_parameters.append(('authResult', data.get('authResult'), 'something'))
        return invalid_parameters

    def _adyen_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('authResult', 'PENDING')
        if status == 'AUTHORISED':
            tx.write({
                'state': 'done',
                'adyen_psp_reference': data.get('pspReference'),
                # 'date_validate': data.get('payment_date', fields.datetime.now()),
                # 'paypal_txn_type': data.get('express_checkout')
            })
            return True
        elif status == 'PENDING':
            tx.write({
                'state': 'pending',
                'adyen_psp_reference': data.get('pspReference'),
            })
            return True
        else:
            error = 'Paypal: feedback error'
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error
            })
            return False
