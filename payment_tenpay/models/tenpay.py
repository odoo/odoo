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

import util
from urllib import urlencode, urlopen

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_tenpay.controllers.main import TenpayController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare
from openerp import SUPERUSER_ID
from openerp.http import request
from openerp import models, fields, api, exceptions, _


_logger = logging.getLogger(__name__)


class AcquirerTenpay(osv.Model):
    _inherit = 'payment.acquirer'

    @api.one
    def _get_ipaddress(self):
        return request.httprequest.environ['REMOTE_ADDR']

    def _get_tenpay_urls(self, cr, uid, environment, context=None):
        """ Tenpay URLS """
        if environment == 'prod':
            return {
                'tenpay_url': 'https://api.tenpay.com'
            }
        else:
            return {
                'tenpay_url': 'https://sandbox.tenpay.com/api'
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerTenpay, self)._get_providers(cr, uid, context=context)
        providers.append(['tenpay', 'Tenpay'])
        return providers



    _columns = {
        'tenpay_partner_account': fields.char('Tenpay AppID', required_if_provider='tenpay'),
        'tenpay_partner_key': fields.char('Tenpay Key', required_if_provider='tenpay'),
        'tenpay_partner_email': fields.char('Tenpay Partner Email', required_if_provider='tenpay'),

    }

    @api.one
    def _get_partner_key(self):
        return self.tenpay_partner_key

    _defaults = {
        'fees_active': False,
        'fees_dom_fixed': 0.0,
        'fees_dom_var': 0.0,
        'fees_int_fixed': 0.0,
        'fees_int_var': 0.0,
    }

    def tenpay_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
        """ Compute tenpay fees.

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

    def tenpay_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        amount = int(tx_values.get('total_fee', 0) * 100)

        tenpay_tx_values = dict(tx_values)
        tenpay_tx_values.update({
            'total_fee': amount,
            'spbill_create_ip': acquirer._get_ipaddress(),
            'partner': acquirer.tenpay_partner_account,
            'out_trade_no': tx_values['reference'],
            'body': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'bank_type': 'DEFAULT',
            'fee_type': 1,
            'input_charset': 'utf-8',
            'return_url': '%s' % urlparse.urljoin(base_url, TenpayController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, TenpayController._notify_url),
        })

        to_sign = {}
        to_sign.update({
            'total_fee': amount,
            'spbill_create_ip': acquirer._get_ipaddress(),
            'partner': acquirer.tenpay_partner_account,
            'out_trade_no': tx_values['reference'],
            'body': '%s: %s' % (acquirer.company_id.name, tx_values['reference']),
            'bank_type': 'DEFAULT',
            'fee_type': 1,
            'input_charset': 'utf-8',
            'return_url': '%s' % urlparse.urljoin(base_url, TenpayController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, TenpayController._notify_url),
        })

        _,prestr = util.params_filter(to_sign)
        tenpay_tx_values['sign'] = util.build_mysign(prestr, acquirer.tenpay_partner_key, 'MD5')
        tenpay_tx_values['sign_type'] = 'MD5'
        context = context
        context['_data_exchange'] = tenpay_tx_values

        return partner_values, tenpay_tx_values

    def tenpay_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        params = context['_data_exchange']
        return self._get_tenpay_urls(cr, uid, acquirer.environment, context=context)['tenpay_url'] + urlencode(params)

class TxTenpay(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'tenpay_txn_id': fields.char('Transaction ID'),
        'tenpay_txn_type': fields.char('Transaction type'),
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _tenpay_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('out_trade_no'), data.get('out_trade_no')
        if not reference or not txn_id:
            error_msg = 'Tenpay: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Tenpay: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    def _tenpay_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('trade_state')
        data = {
            'acquirer_reference': data.get('out_trade_no'),
            'tenpay_txn_id': data.get('out_trade_no'),
            'tenpay_txn_type': data.get('fee_type'),

        }

        if status == 0:
            _logger.info('Validated Tenpay payment for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=data.get('time_end', fields.datetime.now()))
            return tx.write(data)

        else:
            error = 'Received unrecognized status for Tenpay payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)

