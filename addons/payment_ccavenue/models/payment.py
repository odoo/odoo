# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from binascii import hexlify, unhexlify
from hashlib import md5
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_ccavenue.controllers.main import CCAvenueController
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)

try:
    from Crypto.Cipher import AES
except ImportError:
    _logger.info('pyCrypto library not found. If you plan to use payment_ccavenue, please install the library from https://pypi.python.org/pypi/pyCrypto')


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('ccavenue', 'CCAvenue')])
    ccavenue_merchant_id = fields.Char(string='CCAvenue Merchant ID', required_if_provider='ccavenue', groups='base.group_user')
    ccavenue_access_code = fields.Char(string='Access Code', required_if_provider='ccavenue', groups='base.group_user')
    ccavenue_working_key = fields.Char(string='Working Key', required_if_provider='ccavenue', groups='base.group_user')

    def _get_ccavenue_urls(self, environment):
        """ CCAvenue URLs"""
        if environment == 'prod':
            return {'ccavenue_form_url': 'https://secure.ccavenue.com/transaction/transaction.do?command=initiateTransaction'}
        else:
            return {'ccavenue_form_url': 'https://test.ccavenue.com/transaction/transaction.do?command=initiateTransaction'}

    def _ccavenue_pad(self, data):
        length = 16 - (len(data) % 16)
        data += chr(length) * length
        return data

    @api.multi
    def _ccavenue_encrypt_text(self, plaintext):
        self.ensure_one()
        iv = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
        plaintext = self._ccavenue_pad(plaintext)
        dec_digest = md5(self.ccavenue_working_key.encode('utf-8')).digest()
        enc_cipher = AES.new(dec_digest, AES.MODE_CBC, iv)
        encrypted_text = hexlify(enc_cipher.encrypt(plaintext)).decode('utf-8')
        return encrypted_text

    @api.multi
    def _ccavenue_decrypt_text(self, ciphertext):
        self.ensure_one()
        iv = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
        dec_digest = md5(self.ccavenue_working_key.encode('utf-8')).digest()
        dec_cipher = AES.new(dec_digest, AES.MODE_CBC, iv)
        decrypted_text = dec_cipher.decrypt(unhexlify(ciphertext)).decode('utf-8')
        return decrypted_text

    @api.multi
    def ccavenue_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        ccavenue_values = dict(access_code=self.ccavenue_access_code,
                               merchant_id=self.ccavenue_merchant_id,
                               order_id=values.get('reference'),
                               currency=values.get('currency').name,
                               amount=values.get('amount'),
                               redirect_url=urls.url_join(base_url, CCAvenueController._return_url),
                               cancel_url=urls.url_join(base_url, CCAvenueController._cancel_url),
                               language='EN',
                               customer_identifier=values.get('partner_email'),
                               delivery_name=values.get('partner_name'),
                               delivery_address=values.get('partner_address'),
                               delivery_city=values.get('partner_city'),
                               delivery_state=values.get('partner_state').name,
                               delivery_zip=values.get('partner_zip'),
                               delivery_country=values.get('partner_country').name,
                               delivery_tel=values.get('partner_phone'),
                               billing_name=values.get('billing_partner_name'),
                               billing_address=values.get('billing_partner_address'),
                               billing_city=values.get('billing_partner_city'),
                               billing_state=values.get('billing_partner_state').name,
                               billing_zip=values.get('billing_partner_zip'),
                               billing_country=values.get('billing_partner_country').name,
                               billing_tel=values.get('billing_partner_phone'),
                               billing_email=values.get('billing_partner_email'),
                               )
        ccavenue_values['encRequest'] = self._ccavenue_encrypt_text(urls.url_encode(ccavenue_values))
        return ccavenue_values

    @api.multi
    def ccavenue_get_form_action_url(self):
        self.ensure_one()
        return self._get_ccavenue_urls(self.environment)['ccavenue_form_url']


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # Override form_feedback
    @api.model
    def form_feedback(self, data, acquirer_name):
        if acquirer_name == 'ccavenue':
            acquirer = self.env['payment.acquirer'].search([('provider', '=', 'ccavenue')], limit=1)
            data = acquirer._ccavenue_decrypt_text(data.get('encResp'))
            data = urls.url_decode(data)
        return super(PaymentTransaction, self).form_feedback(data=data, acquirer_name=acquirer_name)

    @api.model
    def _ccavenue_form_get_tx_from_data(self, data):
        """ Given a data dict coming from ccavenue, verify it and find the related
        transaction record. """
        reference = data.get('order_id')
        if not reference:
            raise ValidationError(_('CCAvenue: received data with missing reference (%s)') % (reference))

        transaction = self.search([('reference', '=', reference)])
        if not transaction or len(transaction) > 1:
            error_msg = _('CCAvenue: received data for reference %s') % (reference)
            if not transaction:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            raise ValidationError(error_msg)
        return transaction

    @api.model
    def _ccavenue_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if self.acquirer_reference and data.get('order_id') != self.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('order_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('amount', '0.0')), self.amount, precision_digits=2) != 0:
            invalid_parameters.append(('Amount', data.get('amount'), '%.2f' % self.amount))
        return invalid_parameters

    @api.model
    def _ccavenue_form_validate(self, data):
        if self.state == 'done':
            _logger.warning('CCAvenue: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = data.get('order_status')
        if status_code == "Success":
            _logger.info('Validated CCAvenue payment for tx %s: set as done' % (self.reference))
            self.write({'acquirer_reference': data.get('tracking_id')})
            self._set_transaction_done()
            return True
        elif status_code == "Aborted":
            _logger.info('Aborted CCAvenue payment for tx %s: set as cancel' % (self.reference))
            self.write({'acquirer_reference': data.get('tracking_id'), 'state_message': data.get('status_message')})
            self._set_transaction_cancel()
            return False
        else:
            error = data.get('failure_message') or data.get('status_message')
            _logger.info(error)
            self.write({'acquirer_reference': data.get('tracking_id')})
            self._set_transaction_error(error)
            return False
