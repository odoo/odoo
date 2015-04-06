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

import hashlib
import util
import urllib

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_allpay.controllers.main import allPayController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class AcquirerallPay(osv.Model):
    _inherit = 'payment.acquirer'

     @classmethod


    def checkout_feedback(cls, post):
        """
        :param post: post is a dictionary which allPay server sent to us.
        :return: a dictionary containing data the allpay server return to us.
        """
        _logger.info('inside the feedback')
        returns = {}
        ar_parameter = {}
        check_mac_value = ''
        try:
            payment_type_replace_map = {'_CVS': '', '_BARCODE': '', '_Alipay': '', '_Tenpay': '', '_CreditCard': ''}
            period_type_replace_map = {'Y': 'Year', 'M': 'Month', 'D': 'Day'}
            for key, val in post.iteritems():

                print key, val
                if key == 'CheckMacValue':
                    check_mac_value = val
                else:
                    ar_parameter[key.lower()] = val
                    if key == 'PaymentType':
                        for origin, replacement in payment_type_replace_map.iteritems():
                            val = val.replace(origin, replacement)
                    elif key == 'PeriodType':
                        for origin, replacement in period_type_replace_map.iteritems():
                            val = val.replace(origin, replacement)
                    returns[key] = val

            sorted_returns = sorted(ar_parameter.iteritems())
            sz_confirm_mac_value = "HashKey=" + HASH_KEY

            for val in sorted_returns:
                sz_confirm_mac_value = "".join((str(sz_confirm_mac_value), "&", str(val[0]), "=", str(val[1])))

            sz_confirm_mac_value = "".join((sz_confirm_mac_value, "&HashIV=", HASH_IV))
            sz_confirm_mac_value = do_str_replace((urllib.quote_plus(sz_confirm_mac_value)).lower(), False)
            sz_confirm_mac_value = hashlib.md5(sz_confirm_mac_value).hexdigest().upper()

            _logger.info('sz-checkMacValue: %s & checkMacValue: %s' % (sz_confirm_mac_value, check_mac_value))

            if sz_confirm_mac_value != check_mac_value:
                return False
            else:
                return returns
        except:
            _logger.info('Exception!')

    def _get_allpay_urls(self, cr, uid, environment, context=None):
        """ allPay URLS """
        if environment == 'prod':
            return {
                'allpay_url': 'https://payment.allpay.com.tw/Cashier/AioCheckOut'
            }
        else:
            return {
                'allpay_url': 'http://payment-stage.allpay.com.tw/Cashier/AioCheckOut'
            }

    def _get_checkMacValue_urls(self, cr, uid, environment, context=None):
        """ allPay URLS """
        if environment == 'prod':
            return {
                'allpay_url': 'https://payment.allpay.com.tw/AioHelper/GenCheckMacValue'
            }
        else:
            return {
                'allpay_url': 'http://payment-stage.allpay.com.tw/AioHelper/GenCheckMacValue'
            }


    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerallPay, self)._get_providers(cr, uid, context=context)
        providers.append(['allpay', 'allPay'])
        return providers

    _columns = {
        'allpay_merchant_id': fields.char('allPay Merchant ID', required_if_provider='allpay'),
        'allpay_hash_key': fields.char('allPay Hash Key', required_if_provider='allpay'),
        'allpay_hash_iv': fields.char('allPay Hash IV', required_if_provider='allpay'),
    }

    _defaults = {
        'fees_active': False,
        'fees_dom_fixed': 0.0,
        'fees_dom_var': 0.0,
        'fees_int_fixed': 0.0,
        'fees_int_var': 0.0,
    }

    def allpay_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
        """ Compute allpay fees.

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

    def allpay_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        allpay_tx_values = dict(tx_values)
        allpay_tx_values.update({
            'MerchantID': acquirer.allpay_merchant_id,
            'MerchantTradeNo': tx_values['reference'],
            'MerchantTradeDate': tx_values['date_create'],
            'PaymentType': 'aio',
            'TotalAmount': tx_values['amount'],
            'TradeDesc': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'ItemName': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'ChoosePayment': 'ALL',
            'ReturnURL': '%s' % urlparse.urljoin(base_url, allPayController._return_url),
        })

        to_sign = {}
        to_sign.update({
            'MerchantID': acquirer.allpay_merchant_id,
            'MerchantTradeNo': tx_values['reference'],
            'MerchantTradeDate': tx_values['date_create'],
            'PaymentType': 'aio',
            'TotalAmount': tx_values['amount'],
            'TradeDesc': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'ItemName': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'ChoosePayment': 'ALL',
            'ReturnURL': '%s' % urlparse.urljoin(base_url, allPayController._return_url),
        })

        sorted_to_sign = sorted(to_sign.interitems())
        sorted_to_sign.insert(0,('HashKey',acquirer.allpay_hash_key))
        sorted_to_sign.append(('HashIV',acquirer.allpay_hash_iv))

        sorted_to_sign = util.do_str_replace(urllib.quote(urllib.urlencode(sorted_to_sign), '+%').lower())
        _logger.info(urllib.quote(urllib.urlencode(sorted_dict), '+').lower())

        check_mac_value = hashlib.md5(sorted_to_sign).hexdigest().upper()
        allpay_tx_values['CheckMacValue'] = check_mac_value

        return partner_values, allpay_tx_values

    def allpay_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_allpay_urls(cr, uid, acquirer.environment, context=context)['allpay_url']


class TxallPay(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'allpay_txn_id': fields.char('Transaction ID'),
        'allpay_txn_type': fields.char('Transaction type'),
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _allpay_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('out_trade_no'), data.get('trade_no')
        if not reference or not txn_id:
            error_msg = 'allPay: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'allPay: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    def _allpay_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('RtnCode')
        data = {
            'acquirer_reference': data.get('MerchantTradeNo'),
            'allpay_txn_id': data.get('TradeNo'),
            'allpay_txn_type': data.get('PaymentType'),
        }

        if status =1:
            _logger.info('Validated allPay payment for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=data.get('PaymentDate', fields.datetime.now()))
            return tx.write(data)
        elif status = 800:
            _logger.info('Received notification for allPay payment %s: set as pending' % (tx.reference))
            data.update(state='pending', state_message=data.get('RtnMsg', ''))
            return tx.write(data)
        else:
            error = 'Received unrecognized status for allPay payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)

