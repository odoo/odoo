# -*- coding: utf-'8' "-*-"

import base64
import json
import binascii
from collections import OrderedDict
import hashlib
import hmac
import logging
import urlparse

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_adyen.controllers.main import AdyenController
from openerp.osv import osv, fields
from openerp.tools import float_round
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class AcquirerAdyen(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_adyen_urls(self, cr, uid, environment, context=None):
        """ Adyen URLs

         - yhpp: hosted payment page: pay.shtml for single, select.shtml for multiple
        """
        return {
            'adyen_form_url': 'https://%s.adyen.com/hpp/pay.shtml' % ('live' if environment == 'prod' else environment),
        }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerAdyen, self)._get_providers(cr, uid, context=context)
        providers.append(['adyen', 'Adyen'])
        return providers

    _columns = {
        'adyen_merchant_account': fields.char('Merchant Account', required_if_provider='adyen'),
        'adyen_skin_code': fields.char('Skin Code', required_if_provider='adyen'),
        'adyen_skin_hmac_key': fields.char('Skin HMAC Key', required_if_provider='adyen'),
    }

    def _adyen_generate_merchant_sig_sha256(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications., when using the SHA-256
        signature.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (openerp contacting ogone) or 'out' (adyen
                             contacting openerp). In this last case only some
                             fields should be contained (see e-Commerce basic)
        :param dict values: transaction values
        :return string: shasign
        """
        def escapeVal(val):
            return val.replace('\\', '\\\\').replace(':', '\\:')

        def signParams(parms):
            signing_string = ':'.join(map(escapeVal, parms.keys() + parms.values()))
            hm = hmac.new(hmac_key, signing_string, hashlib.sha256)
            return base64.b64encode(hm.digest())

        assert inout in ('in', 'out')
        assert acquirer.provider == 'adyen'

        if inout == 'in':
            # All the fields sent to Adyen must be included in the signature. ALL the fucking
            # fields, despite what is claimed in the documentation. For example, in
            # https://docs.adyen.com/developers/hpp-manual, it is stated: "The resURL parameter does
            # not need to be included in the signature." It's a trap, it must be included as well!
            keys = [
                'merchantReference', 'paymentAmount', 'currencyCode', 'shipBeforeDate', 'skinCode',
                'merchantAccount', 'sessionValidity', 'merchantReturnData', 'shopperEmail',
                'shopperReference', 'allowedMethods', 'blockedMethods', 'offset',
                'shopperStatement', 'recurringContract', 'billingAddressType',
                'deliveryAddressType', 'brandCode', 'countryCode', 'shopperLocale', 'orderData',
                'offerEmail', 'resURL',
            ]
        else:
            keys = [
                'authResult', 'merchantReference', 'merchantReturnData', 'paymentMethod',
                'pspReference', 'shopperLocale', 'skinCode',
            ]

        hmac_key = binascii.a2b_hex(acquirer.adyen_skin_hmac_key.encode('ascii'))
        raw_values = {k: values.get(k.encode('ascii'), '') for k in keys if k in values}
        raw_values_ordered = OrderedDict(sorted(raw_values.items(), key=lambda t: t[0]))

        return signParams(raw_values_ordered)

    def _adyen_generate_merchant_sig(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications, when using the SHA-1
        signature (deprecated by Adyen).

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (openerp contacting ogone) or 'out' (adyen
                             contacting openerp). In this last case only some
                             fields should be contained (see e-Commerce basic)
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.provider == 'adyen'

        if inout == 'in':
            keys = "paymentAmount currencyCode shipBeforeDate merchantReference skinCode merchantAccount sessionValidity shopperEmail shopperReference recurringContract allowedMethods blockedMethods shopperStatement merchantReturnData billingAddressType deliveryAddressType offset".split()
        else:
            keys = "authResult pspReference merchantReference skinCode merchantReturnData".split()

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        sign = ''.join('%s' % get_value(k) for k in keys).encode('ascii')
        key = acquirer.adyen_skin_hmac_key.encode('ascii')
        return base64.b64encode(hmac.new(key, sign, hashlib.sha1).digest())

    def adyen_form_generate_values(self, cr, uid, id, values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        # tmp
        import datetime
        from dateutil import relativedelta

        if acquirer.provider == 'adyen' and len(acquirer.adyen_skin_hmac_key) == 64:
            tmp_date = datetime.datetime.today() + relativedelta.relativedelta(days=1)

            values.update({
                'merchantReference': values['reference'],
                'paymentAmount': '%d' % int(float_round(values['amount'], 2) * 100),
                'currencyCode': values['currency'] and values['currency'].name or '',
                'shipBeforeDate': tmp_date.strftime('%Y-%m-%d'),
                'skinCode': acquirer.adyen_skin_code,
                'merchantAccount': acquirer.adyen_merchant_account,
                'shopperLocale': values.get('partner_lang', ''),
                'sessionValidity': tmp_date.isoformat('T')[:19] + "Z",
                'resURL': '%s' % urlparse.urljoin(base_url, AdyenController._return_url),
                'merchantReturnData': json.dumps({'return_url': '%s' % values.pop('return_url')}) if values.get('return_url', '') else False,
                'shopperEmail': values.get('partner_email', ''),
            })
            values['merchantSig'] = self._adyen_generate_merchant_sig_sha256(acquirer, 'in', values)

        else:
            tmp_date = datetime.date.today() + relativedelta.relativedelta(days=1)

            values.update({
                'merchantReference': values['reference'],
                'paymentAmount': '%d' % int(float_round(values['amount'], 2) * 100),
                'currencyCode': values['currency'] and values['currency'].name or '',
                'shipBeforeDate': tmp_date,
                'skinCode': acquirer.adyen_skin_code,
                'merchantAccount': acquirer.adyen_merchant_account,
                'shopperLocale': values.get('partner_lang'),
                'sessionValidity': tmp_date,
                'resURL': '%s' % urlparse.urljoin(base_url, AdyenController._return_url),
                'merchantReturnData': json.dumps({'return_url': '%s' % values.pop('return_url')}) if values.get('return_url') else False,
                'merchantSig': self._adyen_generate_merchant_sig(acquirer, 'in', values),
            })

        return values

    def adyen_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_adyen_urls(cr, uid, acquirer.environment, context=context)['adyen_form_url']


class TxAdyen(osv.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _adyen_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, pspReference = data.get('merchantReference'), data.get('pspReference')
        if not reference or not pspReference:
            error_msg = _('Adyen: received data with missing reference (%s) or missing pspReference (%s)') % (reference, pspReference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use pspReference ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = _('Adyen: received data for reference %s') % (reference)
            if not tx_ids:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        # verify shasign
        if len(tx.acquirer_id.adyen_skin_hmac_key) == 64:
            shasign_check = self.pool['payment.acquirer']._adyen_generate_merchant_sig_sha256(tx.acquirer_id, 'out', data)
        else:
            shasign_check = self.pool['payment.acquirer']._adyen_generate_merchant_sig(tx.acquirer_id, 'out', data)
        if shasign_check != data.get('merchantSig'):
            error_msg = _('Adyen: invalid merchantSig, received %s, computed %s') % (data.get('merchantSig'), shasign_check)
            _logger.warning(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _adyen_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        # reference at acquirer: pspReference
        if tx.acquirer_reference and data.get('pspReference') != tx.acquirer_reference:
            invalid_parameters.append(('pspReference', data.get('pspReference'), tx.acquirer_reference))
        # seller
        if data.get('skinCode') != tx.acquirer_id.adyen_skin_code:
            invalid_parameters.append(('skinCode', data.get('skinCode'), tx.acquirer_id.adyen_skin_code))
        # result
        if not data.get('authResult'):
            invalid_parameters.append(('authResult', data.get('authResult'), 'something'))

        return invalid_parameters

    def _adyen_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('authResult', 'PENDING')
        if status == 'AUTHORISED':
            tx.write({
                'state': 'done',
                'acquirer_reference': data.get('pspReference'),
                # 'date_validate': data.get('payment_date', fields.datetime.now()),
                # 'paypal_txn_type': data.get('express_checkout')
            })
            return True
        elif status == 'PENDING':
            tx.write({
                'state': 'pending',
                'acquirer_reference': data.get('pspReference'),
            })
            return True
        else:
            error = _('Adyen: feedback error')
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error
            })
            return False
