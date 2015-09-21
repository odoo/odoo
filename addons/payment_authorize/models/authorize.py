# -*- coding: utf-'8' "-*-"

import hashlib
import hmac
import logging
import time
import urlparse

from openerp import api, fields, models
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_authorize.controllers.main import AuthorizeController
from openerp.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentAcquirerAuthorize(models.Model):
    _inherit = 'payment.acquirer'

    def _get_authorize_urls(self, environment):
        """ Authorize URLs """
        if environment == 'prod':
            return {'authorize_form_url': 'https://secure2.authorize.net/gateway/transact.dll'}
        else:
            return {'authorize_form_url': 'https://test.authorize.net/gateway/transact.dll'}

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirerAuthorize, self)._get_providers()
        providers.append(['authorize', 'Authorize.Net'])
        return providers

    authorize_login = fields.Char(string='API Login Id', required_if_provider='authorize')
    authorize_transaction_key = fields.Char(string='API Transaction Key', required_if_provider='authorize')

    def _authorize_generate_hashing(self, values):
        data = '^'.join([
            values['x_login'],
            values['x_fp_sequence'],
            values['x_fp_timestamp'],
            values['x_amount'],
            values['x_currency_code']])
        return hmac.new(str(values['x_trans_key']), data, hashlib.md5).hexdigest()

    @api.multi
    def authorize_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        authorize_tx_values = dict(values)
        temp_authorize_tx_values = {
            'x_login': self.authorize_login,
            'x_trans_key': self.authorize_transaction_key,
            'x_amount': str(values['amount']),
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (self.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': '%s' % urlparse.urljoin(base_url, AuthorizeController._return_url),
            'x_cancel_url': '%s' % urlparse.urljoin(base_url, AuthorizeController._cancel_url),
            'x_currency_code': values['currency'] and values['currency'].name or '',
            'address': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').name or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'phone': values.get('partner_phone'),
            'state': values.get('partner_state') and values['partner_state'].name or '',
        }
        temp_authorize_tx_values['returndata'] = authorize_tx_values.pop('return_url', '')
        temp_authorize_tx_values['x_fp_hash'] = self._authorize_generate_hashing(temp_authorize_tx_values)
        authorize_tx_values.update(temp_authorize_tx_values)
        return authorize_tx_values

    @api.multi
    def authorize_get_form_action_url(self):
        self.ensure_one()
        return self._get_authorize_urls(self.environment)['authorize_form_url']


class TxAuthorize(models.Model):
    _inherit = 'payment.transaction'

    _authorize_valid_tx_status = 1
    _authorize_pending_tx_status = 4
    _authorize_cancel_tx_status = 2

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _authorize_form_get_tx_from_data(self, data):
        """ Given a data dict coming from authorize, verify it and find the related
        transaction record. """
        reference, trans_id, fingerprint = data.get('x_invoice_num'), data.get('x_trans_id'), data.get('x_MD5_Hash')
        if not reference or not trans_id or not fingerprint:
            error_msg = 'Authorize: received data with missing reference (%s) or trans_id (%s) or fingerprint (%s)' % (reference, trans_id, fingerprint)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Authorize: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    @api.model
    def _authorize_form_get_invalid_parameters(self, tx, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('x_trans_id') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('x_trans_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('x_amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('x_amount'), '%.2f' % tx.amount))
        return invalid_parameters

    @api.model
    def _authorize_form_validate(self, tx, data):
        if tx.state == 'done':
            _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % tx.reference)
            return True
        status_code = int(data.get('x_response_code', '0'))
        if status_code == self._authorize_valid_tx_status:
            tx.write({
                'state': 'done',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        elif status_code == self._authorize_pending_tx_status:
            tx.write({
                'state': 'pending',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        elif status_code == self._authorize_cancel_tx_status:
            tx.write({
                'state': 'cancel',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        else:
            error = data.get('x_response_reason_text')
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('x_trans_id'),
            })
            return False
