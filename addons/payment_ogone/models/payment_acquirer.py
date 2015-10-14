# -*- coding: utf-'8' "-*-"

import datetime
from hashlib import sha1
import logging
from lxml import etree, objectify
from openerp.tools.translate import _
from pprint import pformat
import time
from urllib import urlencode
import urllib2
import urlparse

from openerp import SUPERUSER_ID
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_ogone.controllers.main import OgoneController
from openerp.addons.payment_ogone.data import ogone
from openerp.osv import osv, fields
from openerp.tools import float_round, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.float_utils import float_compare, float_repr
from openerp.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class PaymentAcquirerOgone(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_ogone_urls(self, cr, uid, environment, context=None):
        """ Ogone URLS:

         - standard order: POST address for form-based

        @TDETODO: complete me
        """
        return {
            'ogone_standard_order_url': 'https://secure.ogone.com/ncol/%s/orderstandard_utf8.asp' % (environment,),
            'ogone_direct_order_url': 'https://secure.ogone.com/ncol/%s/orderdirect_utf8.asp' % (environment,),
            'ogone_direct_query_url': 'https://secure.ogone.com/ncol/%s/querydirect_utf8.asp' % (environment,),
            'ogone_afu_agree_url': 'https://secure.ogone.com/ncol/%s/AFU_agree.asp' % (environment,),
        }

    def _get_providers(self, cr, uid, context=None):
        providers = super(PaymentAcquirerOgone, self)._get_providers(cr, uid, context=context)
        providers.append(['ogone', 'Ogone'])
        return providers

    _columns = {
        'ogone_pspid': fields.char('PSPID', required_if_provider='ogone'),
        'ogone_userid': fields.char('API User ID', required_if_provider='ogone'),
        'ogone_password': fields.char('API User Password', required_if_provider='ogone'),
        'ogone_shakey_in': fields.char('SHA Key IN', size=32, required_if_provider='ogone'),
        'ogone_shakey_out': fields.char('SHA Key OUT', size=32, required_if_provider='ogone'),
        'ogone_alias_usage': fields.char('Alias Usage', help="""If you want to use Ogone Aliases,
                                                                this default Alias Usage will be presented to
                                                                the customer as the reason you want to
                                                                keep his payment data""")
    }

    def _ogone_generate_shasign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (openerp contacting ogone) or 'out' (ogone
                             contacting openerp). In this last case only some
                             fields should be contained (see e-Commerce basic)
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.provider == 'ogone'
        key = getattr(acquirer, 'ogone_shakey_' + inout)

        def filter_key(key):
            if inout == 'in':
                return True
            else:
                # SHA-OUT keys
                # source https://viveum.v-psp.com/Ncol/Viveum_e-Com-BAS_EN.pdf
                keys = [
                    'AAVADDRESS',
                    'AAVCHECK',
                    'AAVMAIL',
                    'AAVNAME',
                    'AAVPHONE',
                    'AAVZIP',
                    'ACCEPTANCE',
                    'ALIAS',
                    'AMOUNT',
                    'BIC',
                    'BIN',
                    'BRAND',
                    'CARDNO',
                    'CCCTY',
                    'CN',
                    'COMPLUS',
                    'CREATION_STATUS',
                    'CURRENCY',
                    'CVCCHECK',
                    'DCC_COMMPERCENTAGE',
                    'DCC_CONVAMOUNT',
                    'DCC_CONVCCY',
                    'DCC_EXCHRATE',
                    'DCC_EXCHRATESOURCE',
                    'DCC_EXCHRATETS',
                    'DCC_INDICATOR',
                    'DCC_MARGINPERCENTAGE',
                    'DCC_VALIDHOURS',
                    'DIGESTCARDNO',
                    'ECI',
                    'ED',
                    'ENCCARDNO',
                    'FXAMOUNT',
                    'FXCURRENCY',
                    'IBAN',
                    'IP',
                    'IPCTY',
                    'NBREMAILUSAGE',
                    'NBRIPUSAGE',
                    'NBRIPUSAGE_ALLTX',
                    'NBRUSAGE',
                    'NCERROR',
                    'NCERRORCARDNO',
                    'NCERRORCN',
                    'NCERRORCVC',
                    'NCERRORED',
                    'ORDERID',
                    'PAYID',
                    'PM',
                    'SCO_CATEGORY',
                    'SCORING',
                    'STATUS',
                    'SUBBRAND',
                    'SUBSCRIPTION_ID',
                    'TRXDATE',
                    'VC'
                ]
                return key.upper() in keys

        items = sorted((k.upper(), v) for k, v in values.items())
        sign = ''.join('%s=%s%s' % (k, v, key) for k, v in items if v and filter_key(k))
        sign = sign.encode("utf-8")
        shasign = sha1(sign).hexdigest()
        return shasign

    def ogone_form_generate_values(self, cr, uid, id, values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        ogone_tx_values = dict(values)
        temp_ogone_tx_values = {
            'PSPID': acquirer.ogone_pspid,
            'ORDERID': values['reference'],
            'AMOUNT': float_repr(float_round(values['amount'], 2) * 100, 0),
            'CURRENCY': values['currency'] and values['currency'].name or '',
            'LANGUAGE': values.get('partner_lang'),
            'CN': values.get('partner_name'),
            'EMAIL': values.get('partner_email'),
            'OWNERZIP': values.get('partner_zip'),
            'OWNERADDRESS': values.get('partner_address'),
            'OWNERTOWN': values.get('partner_city'),
            'OWNERCTY': values.get('partner_country') and values.get('partner_country').code or '',
            'OWNERTELNO': values.get('partner_phone'),
            'ACCEPTURL': '%s' % urlparse.urljoin(base_url, OgoneController._accept_url),
            'DECLINEURL': '%s' % urlparse.urljoin(base_url, OgoneController._decline_url),
            'EXCEPTIONURL': '%s' % urlparse.urljoin(base_url, OgoneController._exception_url),
            'CANCELURL': '%s' % urlparse.urljoin(base_url, OgoneController._cancel_url),
            'PARAMPLUS': 'return_url=%s' % ogone_tx_values.pop('return_url') if ogone_tx_values.get('return_url') else False,
        }
        if values.get('type') == 'form_save':
            temp_ogone_tx_values.update({
                'ALIAS': 'ODOO-NEW-ALIAS-%s' % time.time(),    # something unique,
                'ALIASUSAGE': values.get('alias_usage') or acquirer.ogone_alias_usage,
            })
        shasign = self._ogone_generate_shasign(acquirer, 'in', temp_ogone_tx_values)
        temp_ogone_tx_values['SHASIGN'] = shasign
        ogone_tx_values.update(temp_ogone_tx_values)
        return ogone_tx_values

    def ogone_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_ogone_urls(cr, uid, acquirer.environment, context=context)['ogone_standard_order_url']

    def ogone_s2s_form_validate(self, cr, uid, id, data, context=None):
        error = dict()
        error_message = []

        mandatory_fields = ["cc_number", "cc_cvc", "cc_holder_name", "cc_expiry", "cc_brand"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        return False if error else True

    def ogone_s2s_form_process(self, cr, uid, data, context=None):
        values = {
            'cc_number': data.get('cc_number'),
            'cc_cvc': int(data.get('cc_cvc')),
            'cc_holder_name': data.get('cc_holder_name'),
            'cc_expiry': data.get('cc_expiry'),
            'cc_brand': data.get('cc_brand'),
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id'))
        }
        pm_id = self.pool['payment.method'].create(cr, SUPERUSER_ID, values, context=context)
        return pm_id
