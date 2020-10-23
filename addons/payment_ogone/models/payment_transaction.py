# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import time
from pprint import pformat

import requests
from lxml import etree, objectify
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_ogone.data import ogone
from odoo.addons.payment.utils import singularize_reference_prefix
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, ustr
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentTxOgone(models.Model):
    _inherit = 'payment.transaction'
    # ogone status
    _ogone_valid_tx_status = [5, 9, 8]
    _ogone_wait_tx_status = [41, 50, 51, 52, 55, 56, 91, 92, 99]
    _ogone_pending_tx_status = [46, 81, 82]   # 46 = 3DS HTML response
    _ogone_cancel_tx_status = [1]

    ogone_html_3ds = fields.Char('3D Secure HTML')
    ogone_user_error = fields.Char('User Friendly State message ')

    @api.model
    def _compute_reference(self, provider, prefix=None, separator='-', **kwargs):
        # Ogone needs singularized references to avoid triggering errors.
        # They only check the ORDERID to detect duplicate transactions, not the buyer, amount, card etc.
        # We could have problems by using multiple Odoo instances using the same Ogone account.
        # Or if the same reference is used several times
        if provider != 'ogone':
            return super()._compute_reference(provider, prefix, separator, **kwargs)

        prefix = prefix and singularize_reference_prefix(prefix)
        return super()._compute_reference(provider, prefix, separator, **kwargs)

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. Create a payment token if an alias is returned."""
        if provider != 'ogone':
            return super()._get_tx_from_feedback_data(provider, data)
        reference, pay_id, shasign, alias = data.get('orderID'), data.get('PAYID'), data.get('SHASIGN'), data.get('ALIAS')
        if not reference or not pay_id or not shasign:
            error_msg = _('Ogone: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use pay_id ?
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('Ogone: received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = tx.acquirer_id._ogone_generate_shasign('out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Ogone: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        if not tx.acquirer_reference:
            tx.acquirer_reference = pay_id

        return tx

        #  _get_invalid_parameters est supprimé et à merger à _get_tx_from_data et _process_feedback_data qui doivent raise des ValidationError si besoin
    def _get_invalid_parameters(self, data):
        if self.provider != 'ogone':
            return super()._get_invalid_parameters(data)
        invalid_parameters = []
        if self.acquirer_reference and data.get('PAYID') != self.acquirer_reference:
            invalid_parameters.append(('PAYID', data.get('PAYID'), self.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))

        return invalid_parameters

    def _process_feedback_data(self, data):
        if self.provider != 'ogone':
            return super()._process_feedback_data(data)

        if self.state not in ['draft', 'pending']:
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = int(data.get('STATUS', '0'))
        if status in self._ogone_valid_tx_status:
            self.write({
                'acquirer_reference': data.get('PAYID'),
            })
            if self.token_id:
                self.token_id.verified = True
            self._set_done()
            return True
        elif status in self._ogone_cancel_tx_status:
            self._set_canceled()
        elif status in self._ogone_pending_tx_status or status in self._ogone_wait_tx_status:
            self._set_pending()
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERRORPLUS'),
                'error_code': data.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(data.get('NCERROR')),
            }
            _logger.info(error)
            self._set_canceled()
            return False

    # --------------------------------------------------
    # Ogone API RELATED METHODS
    # --------------------------------------------------
    def _send_payment_request(self):
        super()._send_payment_request()  # Log the 'sent' message
        if self.provider != 'ogone':
            return
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)
        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': int(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'SAL',
            'ECI': 9,   # Recurring (from eCommerce)
            'ALIAS': self.token_id.acquirer_ref,
            'RTIMEOUT': 30,
            'EMAIL': self.partner_id.email or '',
            'CN': self.partner_id.name or '',
        }
        data.update({
            'FLAG3D': 'Y',
            'LANGUAGE': self.partner_id.lang or 'en_US',
            'WIN3DS': 'MAINW',
        })
        if request:
            data['REMOTE_ADDR'] = request.httprequest.remote_addr
        data['SHASIGN'] = self.acquirer_id._ogone_generate_shasign('in', data)

        direct_order_url = self.acquirer_id._ogone_get_urls()['ogone_direct_order_url']

        logged_data = data.copy()
        logged_data.pop('PSWD')
        _logger.info("ogone_payment_request: Sending values to URL %s, values:\n%s", direct_order_url, pformat(logged_data))
        result = requests.post(direct_order_url, data=data).content

        try:
            tree = objectify.fromstring(result)
            _logger.info('ogone_payment_request: Values received:\n%s', etree.tostring(tree, pretty_print=True, encoding='utf-8'))
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            _logger.info('ogone_payment_request: Values received:\n%s', result)
            raise

        return self._ogone_validate_tree(tree)

    def _send_refund_request(self, **kwargs):
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)
        data = {
            'PSPID': account.sudo().ogone_pspid,
            'USERID': account.sudo().ogone_userid,
            'PSWD': account.sudo().ogone_password,
            'ORDERID': reference,
            'AMOUNT': int(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'RFS',
            'PAYID': self.acquirer_reference,
        }
        data['SHASIGN'] = self.acquirer_id.sudo()._ogone_generate_shasign('in', data)
        refund_order_url = self.acquirer_id._ogone_get_urls()['ogone_maintenance_url']
        logged_data = data.copy()
        logged_data.pop('PSWD')
        _logger.info("ogone_s2s_do_refund: Sending values to URL %s, values:\n%s", refund_order_url, pformat(logged_data))
        result = requests.post(refund_order_url, data=data).content

        try:
            tree = objectify.fromstring(result)
            _logger.info('ogone_s2s_do_refund: Values received:\n%s', etree.tostring(tree, pretty_print=True, encoding='utf-8'))
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            _logger.info('ogone_s2s_do_refund: Values received:\n%s', result)
            self.state_message = str(result)
            raise

        return self._ogone_validate_tree(tree)

    def _ogone_validate_tree(self, tree, tries=2):
        if self.state not in ['draft', 'pending']:
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = int(tree.get('STATUS') or 0)
        if status in self._ogone_valid_tx_status:
            self.write({
                'acquirer_reference': tree.get('PAYID'),
            })
            if self.token_id:
                self.token_id.verified = True
            self._set_done()
            return True
        elif status in self._ogone_cancel_tx_status:
            self.write({'acquirer_reference': tree.get('PAYID')})
            self._set_canceled()
        elif status in self._ogone_pending_tx_status:
            vals = {
                'acquirer_reference': tree.get('PAYID'),
            }
            if status == 46: # HTML 3DS
                vals['ogone_html_3ds'] = ustr(base64.b64decode(tree.HTML_ANSWER.text))
            self.write(vals)
            self._set_pending()
            return False
        elif status in self._ogone_wait_tx_status and tries > 0:
            time.sleep(0.5)
            self.write({'acquirer_reference': tree.get('PAYID')})
            tree = self._ogone_api_get_tx_status()
            return self._ogone_validate_tree(tree, tries - 1)
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': tree.get('NCERRORPLUS'),
                'error_code': tree.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(tree.get('NCERROR')),
            }

            _logger.info(error)
            self.write({
                'state_message': error,
                'acquirer_reference': tree.get('PAYID'),
                'ogone_user_error':  _("%s" % ogone.OGONE_ERROR_MAP.get(tree.get('NCERROR'))),
            })
            self._set_canceled()
            return False

    def _ogone_api_get_tx_status(self):
        account = self.acquirer_id
        #reference = tx.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%Y%m%d_%H%M%S'), tx.partner_id.id)
        data = {
            'PAYID': self.acquirer_reference,
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
        }

        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % ('prod' if self.acquirer_id.state == 'enabled' else 'test')

        logged_data = data.copy()
        logged_data.pop('PSWD')

        _logger.info("_ogone_api_get_tx_status: Sending values to URL %s, values:\n%s", query_direct_url, pformat(logged_data))
        result = requests.post(query_direct_url, data=data).content

        try:
            tree = objectify.fromstring(result)
            _logger.info('_ogone_api_get_tx_status: Values received:\n%s', etree.tostring(tree, pretty_print=True, encoding='utf-8'))
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            _logger.info('_ogone_api_get_tx_status: Values received:\n%s', result)
            raise

        return tree
