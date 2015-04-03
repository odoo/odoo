# -*- coding: utf-'8' "-*-"

import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import urlparse
import werkzeug.urls
import urllib2
from urllib import urlencode, urlopen

try:
    import hashlib
    md5_constructor = hashlib.md5
    md5_hmac = md5_constructor
    sha_constructor = hashlib.sha1
    sha_hmac = sha_constructor
except ImportError:
    import md5
    md5_constructor = md5.new
    md5_hmac = md5
    import sha
    sha_constructor = sha.new
    sha_hmac = sha

md5 = md5_constructor

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_alipay.controllers.main import AlipayController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

def params_filter(params):
    ks = params.keys()
    ks.sort()
    newparams = {}
    prestr = ''
    for k in ks:
        v = params[k]
        k = smart_str(k, 'utf-8')
        if k not in ('sign','sign_type') and v != '':
            newparams[k] = smart_str(v, 'utf-8')
            prestr += '%s=%s&' % (k, newparams[k])
    prestr = prestr[:-1]
    return newparams, prestr

def build_mysign(prestr, key, sign_type = 'MD5'):
    if sign_type == 'MD5':
        return md5(prestr + key).hexdigest()
    return ''

class AcquirerAlipay(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_alipay_urls(self, cr, uid, environment, context=None):
        """ Alipay URLS """
        if environment == 'prod':
            return {
                'alipay_url': 'https://mapi.alipay.com/gateway.do?'
            }
        else:
            return {
                'alipay_url': 'https://openapi.alipaydev.com/gateway.do?'
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerAlipay, self)._get_providers(cr, uid, context=context)
        providers.append(['alipay', 'Alipay'])
        return providers

    _columns = {
        'alipay_partner_account': fields.char('Alipay Partner ID', required_if_provider='alipay'),
        'alipay_partner_key': fields.char('Alipay Partner Key', required_if_provider='alipay'),
        'alipay_seller_email': fields.char('Alipay Seller Email', required_if_provider='alipay'),

    }

    _defaults = {
        'fees_active': False,
        'fees_dom_fixed': 0.0,
        'fees_dom_var': 0.0,
        'fees_int_fixed': 0.0,
        'fees_int_var': 0.0,

    }

    def alipay_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
        """ Compute alipay fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        acquirer = self.browse(cr, uid, id, context=context)
        if not acquirer.fees_active:
            return 0.0
        country = self.pool['res.country'].browse(cr, uid, country_id, context=context)
        if country and acquirer.company_id.country_id.id == country.id:
            percentage = acquirer.fees_dom_var
            fixed = acquirer.fees_dom_fixed
        else:
            percentage = acquirer.fees_int_var
            fixed = acquirer.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed ) / (1 - percentage / 100.0)
        return fees

    def alipay_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        alipay_tx_values = dict(tx_values)
        alipay_tx_values.update({
            'out_trade_no': tx_values['reference'],
            'subject': tx_values['reference'],
            'service': 'create_direct_pay_by_user',
            'payment_type': '1',
            'partner': acquirer.alipay_seller_email,
            'seller_email': acquirer.alipay_partner_account,
            '_input_charset': 'utf-8',
            'body': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'total_fee': tx_values['amount'],
            'payment_method': 'directPay',
            'defaultbank': '',
            'anti_phishing_key': '',
            'buyer_email': partner_values['email'],
            'extra_common_param': '',
            'royalty_type': '',
            'royalty_parameters': '',
            'return_url': '%s' % urlparse.urljoin(base_url, AlipayController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, AlipayController._notify_url),
            'show_url': '',
        })
        if acquirer.fees_active:
            alipay_tx_values['handling'] = '%.2f' % alipay_tx_values.pop('fees', 0.0)
        if alipay_tx_values.get('return_url'):
            alipay_tx_values['custom'] = json.dumps({'return_url': '%s' % alipay_tx_values.pop('return_url')})

        context['alipay_tx_values'] = alipay_tx_values
        return partner_values, alipay_tx_values

    def alipay_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        params = context['alipay_tx_values']
        params,prestr = params_filter(params)
        params['sign'] = build_mysign(prestr, acquirer.alipay_partner_key, 'MD5')
        params['sign_type'] = 'MD5'

        return self._get_alipay_urls(cr, uid, acquirer.environment, context=context)['alipay_url'] + urlencode(params)

class TxAlipay(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'alipay_txn_id': fields.char('Transaction ID'),
        'alipay_txn_type': fields.char('Transaction type'),
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _alipay_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('item_number'), data.get('txn_id')
        if not reference or not txn_id:
            error_msg = 'Alipay: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Alipay: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    def _alipay_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []
        if data.get('notify_version')[0] != '3.4':
            _logger.warning(
                'Received a notification from Alipay with version %s instead of 2.6. This could lead to issues when managing it.' %
                data.get('notify_version')
            )
        if data.get('test_ipn'):
            _logger.warning(
                'Received a notification from Alipay using sandbox'
            ),

        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        if tx.acquirer_reference and data.get('txn_id') != tx.acquirer_reference:
            invalid_parameters.append(('txn_id', data.get('txn_id'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('mc_gross', '0.0')), (tx.amount + tx.fees), 2) != 0:
            invalid_parameters.append(('mc_gross', data.get('mc_gross'), '%.2f' % tx.amount))  # mc_gross is amount + fees
        if data.get('mc_currency') != tx.currency_id.name:
            invalid_parameters.append(('mc_currency', data.get('mc_currency'), tx.currency_id.name))
        if 'handling_amount' in data and float_compare(float(data.get('handling_amount')), tx.fees, 2) != 0:
            invalid_parameters.append(('handling_amount', data.get('handling_amount'), tx.fees))
        # check buyer
        if tx.partner_reference and data.get('payer_id') != tx.partner_reference:
            invalid_parameters.append(('payer_id', data.get('payer_id'), tx.partner_reference))
        # check seller
        if data.get('receiver_email') != tx.acquirer_id.alipay_partner_account:
            invalid_parameters.append(('receiver_email', data.get('receiver_email'), tx.acquirer_id.alipay_partner_account))
        if data.get('receiver_id') and tx.acquirer_id.alipay_seller_email and data['receiver_id'] != tx.acquirer_id.alipay_seller_email:
            invalid_parameters.append(('receiver_id', data.get('receiver_id'), tx.acquirer_id.alipay_seller_email))

        return invalid_parameters

    def _alipay_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('payment_status')
        data = {
            'acquirer_reference': data.get('txn_id'),
            'alipay_txn_type': data.get('payment_type'),
            'partner_reference': data.get('payer_id')
        }
        if status in ['Completed', 'Processed']:
            _logger.info('Validated Alipay payment for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=data.get('payment_date', fields.datetime.now()))
            return tx.write(data)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Alipay payment %s: set as pending' % (tx.reference))
            data.update(state='pending', state_message=data.get('pending_reason', ''))
            return tx.write(data)
        else:
            error = 'Received unrecognized status for Alipay payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)

