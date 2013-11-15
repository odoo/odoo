# -*- coding: utf-'8' "-*-"
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from hashlib import sha1
import logging
from lxml import etree, objectify
from pprint import pformat
# import requests
import time
from urllib import urlencode
import urllib2
import urlparse

from openerp.addons.payment_acquirer.models.payment_acquirer import ValidationError
from openerp.addons.payment_acquirer_ogone.controllers.main import OgoneController
from openerp.addons.payment_acquirer_ogone.data import ogone
from openerp.osv import osv, fields
from openerp.tools import float_round

_logger = logging.getLogger(__name__)


class PaymentAcquirerOgone(osv.Model):
    _inherit = 'payment.acquirer'

    def _get_ogone_urls(self, cr, uid, ids, name, args, context=None):
        """ Ogone URLS:

         - standard order: POST address for form-based

        @TDETODO: complete me
        """
        res = {}
        for acquirer in self.browse(cr, uid, ids, context=context):
            qualif = acquirer.env
            res[acquirer.id] = {
                'ogone_standard_order_url': 'https://secure.ogone.com/ncol/%s/orderstandard.asp' % qualif,
                'ogone_direct_order_url': 'https://secure.ogone.com/ncol/%s/orderdirect.asp' % qualif,
                'ogone_direct_query_url': 'https://secure.ogone.com/ncol/%s/querydirect.asp' % qualif,
                'ogone_afu_agree_url': 'https://secure.ogone.com/ncol/%s/AFU_agree.asp' % qualif,
            }
        return res

    _columns = {
        'ogone_pspid': fields.char(
            'PSPID', required_if_provider='ogone'),
        'ogone_userid': fields.char(
            'API User id', required_if_provider='ogone'),
        'ogone_password': fields.char(
            'Password', required_if_provider='ogone'),
        'ogone_shakey_in': fields.char(
            'SHA Key IN', size=32, required_if_provider='ogone'),
        'ogone_shakey_out': fields.char(
            'SHA Key OUT', size=32, required_if_provider='ogone'),
        # store ogone contact URLs -> not necessary IMHO
        'ogone_standard_order_url': fields.function(
            _get_ogone_urls, type='char', multi='_get_ogone_urls',
            string='Stanrd Order URL (form)'),
        'ogone_direct_order_url': fields.function(
            _get_ogone_urls, type='char', multi='_get_ogone_urls',
            string='Direct Order URL (2)'),
        'ogone_direct_query_url': fields.function(
            _get_ogone_urls, type='char', multi='_get_ogone_urls',
            string='Direct Query URL'),
        'ogone_afu_agree_url': fields.function(
            _get_ogone_urls, type='char', multi='_get_ogone_urls',
            string='AFU Agree URL'),
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
        assert acquirer.name == 'ogone'
        key = getattr(acquirer, 'ogone_shakey_' + inout)

        def filter_key(key):
            if inout == 'in':
                return True
            else:
                keys = "ORDERID CURRENCY AMOUNT PM ACCEPTANCE STATUS CARDNO ALIAS ED CN TRXDATE PAYID NCERROR BRAND ECI IP COMPLUS".split()
                return key.upper() in keys

        items = sorted((k.upper(), v) for k, v in values.items())
        sign = ''.join('%s=%s%s' % (k, v, key) for k, v in items if v and filter_key(k))
        shasign = sha1(sign).hexdigest()
        return shasign

    def ogone_form_generate_values(self, cr, uid, id, reference, amount, currency, partner_id=False, partner_values=None, tx_custom_values=None, context=None):
        if partner_values is None:
            partner_values = {}
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        partner = None
        if partner_id:
            partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
        tx_values = {
            'PSPID': acquirer.ogone_pspid,
            'ORDERID': reference,
            'AMOUNT': '%d' % int(float_round(amount, 2) * 100),
            'CURRENCY': currency and currency.name or 'EUR',
            'LANGUAGE': partner and partner.lang or partner_values.get('lang', ''),
            'CN': partner and partner.name or partner_values.get('name', ''),
            'EMAIL': partner and partner.email or partner_values.get('email', ''),
            'OWNERZIP': partner and partner.zip or partner_values.get('zip', ''),
            'OWNERADDRESS': partner and ' '.join((partner.street or '', partner.street2 or '')).strip() or ' '.join((partner_values.get('street', ''), partner_values.get('street2', ''))).strip(),
            'OWNERTOWN': partner and partner.city or partner_values.get('city', ''),
            'OWNERCTY': partner and partner.country_id and partner.country_id.name or partner_values.get('country_name', ''),
            'OWNERTELNO': partner and partner.phone or partner_values.get('phone', ''),
            'ACCEPTURL': '%s' % urlparse.urljoin(base_url, OgoneController._accept_url),
            'DECLINEURL': '%s' % urlparse.urljoin(base_url, OgoneController._decline_url),
            'EXCEPTIONURL': '%s' % urlparse.urljoin(base_url, OgoneController._exception_url),
            'CANCELURL': '%s' % urlparse.urljoin(base_url, OgoneController._cancel_url),
        }
        if tx_custom_values and tx_custom_values.get('return_url'):
            tx_values['PARAMPLUS'] = 'return_url=%s' % tx_custom_values.pop('return_url')
        if tx_custom_values:
            tx_values.update(tx_custom_values)
        shasign = self._ogone_generate_shasign(acquirer, 'in', tx_values)
        tx_values['SHASIGN'] = shasign
        return tx_values

    def ogone_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return acquirer.ogone_standard_order_url


class PaymentTxOgone(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'ogone_3ds': fields.dummy('3ds Activated'),
        'ogone_3ds_html': fields.html('3DS HTML'),
        'ogone_feedback_model': fields.char(),
        'ogone_feedback_eval': fields.char(),
        'ogone_complus': fields.char('Complus'),
        'ogone_payid': fields.char()
    }

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def ogone_form_generate_values(self, cr, uid, id, tx_custom_values=None, context=None):
        """ Ogone-specific value generation for rendering a transaction-based
        form button. """
        tx = self.browse(cr, uid, id, context=context)

        tx_data = {
            'LANGUAGE': tx.partner_lang,
            'CN': tx.partner_name,
            'EMAIL': tx.partner_email,
            'OWNERZIP': tx.partner_zip,
            'OWNERADDRESS': tx.partner_address,
            'OWNERTOWN': tx.partner_city,
            'OWNERCTY': tx.partner_country_id and tx.partner_country_id.name or '',
            'OWNERTELNO': tx.partner_phone,
        }
        if tx_custom_values:
            tx_data.update(tx_custom_values)
        return self.pool['payment.acquirer'].ogone_form_generate_values(
            cr, uid, tx.acquirer_id.id,
            tx.reference, tx.amount, tx.currency_id,
            tx_custom_values=tx_data,
            context=context
        )

    def _ogone_form_get_tx_from_shasign_out(self, cr, uid, data, context=None):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. """
        reference, pay_id, shasign = data.get('orderID'), data.get('PAYID'), data.get('SHASIGN')
        if not reference or not pay_id or not shasign:
            error_msg = 'Ogone: received data with missing reference (%s) or pay_id (%s) or shashign (%s)' % (reference, pay_id, shasign)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use paytid ?
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
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

    def ogone_form_feedback(self, cr, uid, data, context=None):
        tx = self._ogone_form_get_tx_from_shasign_out(cr, uid, data, context)
        if not tx:
            raise ValidationError('Ogone: feedback: tx not found')
        if tx.state == 'done':
            _logger.warning('Ogone: trying to validate an already validated tx (ref %s' % tx.reference)
            return False

        status = int(data.get('STATUS', '0'))
        if status in [5, 9]:
            tx.write({
                'state': 'done',
                'date_validate': data['TRXDATE'],
                'ogone_payid': data['PAYID'],
            })
            return True
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERROR'),
                'error_code': data.get('NCERRORPLUS'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(data.get('NCERRORPLUS')),
            }
            _logger.info(error)
            tx.write({'state': 'error', 'state_message': error})
            return False

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------

    def ogone_s2s_create_alias(self, cr, uid, id, values, context=None):
        """ Purpose: create an alias via batch """
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
        pass

    def ogone_s2s_execute(self, cr, uid, id, values, context=None):
        tx = self.browse(cr, uid, id, context=context)

        tx_data = self.ogone_s2s_generate_values(cr, uid, id, values, context=context)
        _logger.info('Generated Ogone s2s data %s', pformat(tx_data))  # debug

        request = urllib2.Request(tx.acquirer_id.ogone_direct_order_url, urlencode(tx_data))
        result = urllib2.urlopen(request).read()
        _logger.info('Contacted Ogone direct order; result %s', result)  # debug

        tree = objectify.fromstring(result)
        payid = tree.get('PAYID')
        print 'payid', payid

        query_direct_data = dict(
            PSPID=tx.acquirer_id.ogone_pspid,
            USERID=tx.acquirer_id.ogone_userid,
            PSWD=tx.acquirer_id.ogone_password,
            ID=payid,
        )
        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % (tx.acquirer_id.env,)

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
