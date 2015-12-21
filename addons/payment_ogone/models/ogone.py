# -*- coding: utf-'8' "-*-"

from hashlib import sha1
import logging
from lxml import etree, objectify
from pprint import pformat
import time
from datetime import datetime
from urllib import urlencode
import urllib2
import urlparse

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_ogone.controllers.main import OgoneController
from openerp.addons.payment_ogone.data import ogone
from openerp.osv import osv, fields
from openerp.tools import float_round, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.float_utils import float_compare, float_repr

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

    def ogone_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        ogone_tx_values = dict(tx_values)
        temp_ogone_tx_values = {
            'PSPID': acquirer.ogone_pspid,
            'ORDERID': tx_values['reference'],
            'AMOUNT': float_repr(float_round(tx_values['amount'], 2) * 100, 0),
            'CURRENCY': tx_values['currency'] and tx_values['currency'].name or '',
            'LANGUAGE':  partner_values['lang'],
            'CN':  partner_values['name'],
            'EMAIL':  partner_values['email'],
            'OWNERZIP':  partner_values['zip'],
            'OWNERADDRESS':  partner_values['address'],
            'OWNERTOWN':  partner_values['city'],
            'OWNERCTY':  partner_values['country'] and partner_values['country'].code or '',
            'OWNERTELNO': partner_values['phone'],
            'ACCEPTURL': '%s' % urlparse.urljoin(base_url, OgoneController._accept_url),
            'DECLINEURL': '%s' % urlparse.urljoin(base_url, OgoneController._decline_url),
            'EXCEPTIONURL': '%s' % urlparse.urljoin(base_url, OgoneController._exception_url),
            'CANCELURL': '%s' % urlparse.urljoin(base_url, OgoneController._cancel_url),
        }
        if ogone_tx_values.get('return_url'):
            temp_ogone_tx_values['PARAMPLUS'] = 'return_url=%s' % ogone_tx_values.pop('return_url')
        shasign = self._ogone_generate_shasign(acquirer, 'in', temp_ogone_tx_values)
        temp_ogone_tx_values['SHASIGN'] = shasign
        ogone_tx_values.update(temp_ogone_tx_values)
        return partner_values, ogone_tx_values

    def ogone_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_ogone_urls(cr, uid, acquirer.environment, context=context)['ogone_standard_order_url']


class PaymentTxOgone(osv.Model):
    _inherit = 'payment.transaction'
    # ogone status
    _ogone_valid_tx_status = [5, 9]
    _ogone_wait_tx_status = [41, 50, 51, 52, 55, 56, 91, 92, 99]
    _ogone_pending_tx_status = [46]   # 3DS HTML response
    _ogone_cancel_tx_status = [1]

    _columns = {
        'ogone_3ds': fields.boolean('3DS Activated'),
        'ogone_3ds_html': fields.html('3DS HTML'),
        'ogone_complus': fields.char('Complus'),
        'ogone_payid': fields.char('PayID', help='Payment ID, generated by Ogone')
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _ogone_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. """
        reference, pay_id, shasign = data.get('orderID'), data.get('PAYID'), data.get('SHASIGN')
        if not reference or not pay_id or not shasign:
            error_msg = 'Ogone: received data with missing reference (%s) or pay_id (%s) or shashign (%s)' % (reference, pay_id, shasign)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use paytid ?
        tx_ids = self.search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Ogone: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        # verify shasign
        shasign_check = self.pool['payment.acquirer']._ogone_generate_shasign(tx.acquirer_id, 'out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = 'Ogone: invalid shasign, received %s, computed %s, for data %s' % (shasign, shasign_check, data)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _ogone_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        # TODO: txn_id: should be false at draft, set afterwards, and verified with txn details
        if tx.acquirer_reference and data.get('PAYID') != tx.acquirer_reference:
            invalid_parameters.append(('PAYID', data.get('PAYID'), tx.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % tx.amount))
        if data.get('currency') != tx.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), tx.currency_id.name))

        return invalid_parameters

    def _ogone_form_validate(self, cr, uid, tx, data, context=None):
        if tx.state == 'done':
            _logger.warning('Ogone: trying to validate an already validated tx (ref %s)' % tx.reference)
            return True

        status = int(data.get('STATUS', '0'))
        if status in self._ogone_valid_tx_status:
            tx.write({
                'state': 'done',
                'date_validate': datetime.strptime(data['TRXDATE'],'%m/%d/%y').strftime(DEFAULT_SERVER_DATE_FORMAT),
                'acquirer_reference': data['PAYID'],
            })
            return True
        elif status in self._ogone_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'acquirer_reference': data.get('PAYID'),
            })
        elif status in self._ogone_pending_tx_status or status in self._ogone_wait_tx_status:
            tx.write({
                'state': 'pending',
                'acquirer_reference': data.get('PAYID'),
            })
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERRORPLUS'),
                'error_code': data.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(data.get('NCERROR')),
            }
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('PAYID'),
            })
            return False

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------

    def ogone_s2s_create_alias(self, cr, uid, id, values, context=None):
        """ Create an alias at Ogone via batch.

         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        tx = self.browse(cr, uid, id, context=context)
        assert tx.type == 'server2server', 'Calling s2s dedicated method for a %s acquirer' % tx.type
        alias = 'OPENERP-%d-%d' % (tx.partner_id.id, tx.id)

        expiry_date = '%s%s' % (values['expiry_date_mm'], values['expiry_date_yy'][2:])
        line = 'ADDALIAS;%(alias)s;%(holder_name)s;%(number)s;%(expiry_date)s;%(brand)s;%(pspid)s'
        line = line % dict(values, alias=alias, expiry_date=expiry_date, pspid=tx.acquirer_id.ogone_pspid)

        tx_data = {
            'FILE_REFERENCE': 'OPENERP-NEW-ALIAS-%s' % time.time(),    # something unique,
            'TRANSACTION_CODE': 'ATR',
            'OPERATION': 'SAL',
            'NB_PAYMENTS': 1,   # even if we do not actually have any payment, ogone want it to not be 0
            'FILE': line,
            'REPLY_TYPE': 'XML',
            'PSPID': tx.acquirer_id.ogone_pspid,
            'USERID': tx.acquirer_id.ogone_userid,
            'PSWD': tx.acquirer_id.ogone_password,
            'PROCESS_MODE': 'CHECKANDPROCESS',
        }

        # TODO: fix URL computation
        request = urllib2.Request(tx.acquirer_id.ogone_afu_agree_url, urlencode(tx_data))
        result = urllib2.urlopen(request).read()

        try:
            tree = objectify.fromstring(result)
        except etree.XMLSyntaxError:
            _logger.exception('Invalid xml response from ogone')
            return None

        error_code = error_str = None
        if hasattr(tree, 'PARAMS_ERROR'):
            error_code = tree.NCERROR.text
            error_str = 'PARAMS ERROR: %s' % (tree.PARAMS_ERROR.text or '',)
        else:
            node = tree.FORMAT_CHECK
            error_node = getattr(node, 'FORMAT_CHECK_ERROR', None)
            if error_node is not None:
                error_code = error_node.NCERROR.text
                error_str = 'CHECK ERROR: %s' % (error_node.ERROR.text or '',)

        if error_code:
            error_msg = ogone.OGONE_ERROR_MAP.get(error_code)
            error = '%s\n\n%s: %s' % (error_str, error_code, error_msg)
            _logger.error(error)
            raise Exception(error)      # TODO specific exception

        tx.write({'partner_reference': alias})
        return True

    def ogone_s2s_generate_values(self, cr, uid, id, custom_values, context=None):
        """ Generate valid Ogone values for a s2s tx.

         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        tx = self.browse(cr, uid, id, context=context)
        tx_data = {
            'PSPID': tx.acquirer_id.ogone_pspid,
            'USERID': tx.acquirer_id.ogone_userid,
            'PSWD': tx.acquirer_id.ogone_password,
            'OrderID': tx.reference,
            'amount':  '%d' % int(float_round(tx.amount, 2) * 100),  # tde check amount or str * 100 ?
            'CURRENCY': tx.currency_id.name,
            'LANGUAGE': tx.partner_lang,
            'OPERATION': 'SAL',
            'ECI': 2,   # Recurring (from MOTO)
            'ALIAS': tx.partner_reference,
            'RTIMEOUT': 30,
        }
        if custom_values.get('ogone_cvc'):
            tx_data['CVC'] = custom_values.get('ogone_cvc')
        if custom_values.pop('ogone_3ds', None):
            tx_data.update({
                'FLAG3D': 'Y',   # YEAH!!
            })
            if custom_values.get('ogone_complus'):
                tx_data['COMPLUS'] = custom_values.get('ogone_complus')
            if custom_values.get('ogone_accept_url'):
                pass

        shasign = self.pool['payment.acquirer']._ogone_generate_shasign(tx.acquirer_id, 'in', tx_data)
        tx_data['SHASIGN'] = shasign
        return tx_data

    def ogone_s2s_feedback(self, cr, uid, data, context=None):
        """
         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        pass

    def ogone_s2s_execute(self, cr, uid, id, values, context=None):
        """
         .. versionadded:: pre-v8 saas-3
         .. warning::

            Experimental code. You should not use it before OpenERP v8 official
            release.
        """
        tx = self.browse(cr, uid, id, context=context)

        tx_data = self.ogone_s2s_generate_values(cr, uid, id, values, context=context)
        _logger.debug('Generated Ogone s2s data %s', pformat(tx_data))

        request = urllib2.Request(tx.acquirer_id.ogone_direct_order_url, urlencode(tx_data))
        result = urllib2.urlopen(request).read()
        _logger.debug('Contacted Ogone direct order; result %s', result)

        tree = objectify.fromstring(result)
        payid = tree.get('PAYID')

        query_direct_data = dict(
            PSPID=tx.acquirer_id.ogone_pspid,
            USERID=tx.acquirer_id.ogone_userid,
            PSWD=tx.acquirer_id.ogone_password,
            ID=payid,
        )
        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % (tx.acquirer_id.environment,)

        tries = 2
        tx_done = False
        tx_status = False
        while not tx_done or tries > 0:
            try:
                tree = objectify.fromstring(result)
            except etree.XMLSyntaxError:
                # invalid response from ogone
                _logger.exception('Invalid xml response from ogone')
                raise

            # see https://secure.ogone.com/ncol/paymentinfos1.asp
            VALID_TX = [5, 9]
            WAIT_TX = [41, 50, 51, 52, 55, 56, 91, 92, 99]
            PENDING_TX = [46]   # 3DS HTML response
            # other status are errors...

            status = tree.get('STATUS')
            if status == '':
                status = None
            else:
                status = int(status)

            if status in VALID_TX:
                tx_status = True
                tx_done = True

            elif status in PENDING_TX:
                html = str(tree.HTML_ANSWER)
                tx_data.update(ogone_3ds_html=html.decode('base64'))
                tx_status = False
                tx_done = True

            elif status in WAIT_TX:
                time.sleep(1500)

                request = urllib2.Request(query_direct_url, urlencode(query_direct_data))
                result = urllib2.urlopen(request).read()
                _logger.debug('Contacted Ogone query direct; result %s', result)

            else:
                error_code = tree.get('NCERROR')
                if not ogone.retryable(error_code):
                    error_str = tree.get('NCERRORPLUS')
                    error_msg = ogone.OGONE_ERROR_MAP.get(error_code)
                    error = 'ERROR: %s\n\n%s: %s' % (error_str, error_code, error_msg)
                    _logger.info(error)
                    raise Exception(error)

            tries = tries - 1

        if not tx_done and tries == 0:
            raise Exception('Cannot get transaction status...')

        return tx_status
