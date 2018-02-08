# coding: utf-8
from werkzeug import urls

from .authorize_request import AuthorizeAPI
from datetime import datetime
import hashlib
import hmac
import logging
import time

from odoo import _, api, fields, models
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_authorize.controllers.main import AuthorizeController
from odoo.tools.float_utils import float_compare
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class PaymentAcquirerAuthorize(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('authorize', 'Authorize.Net')])
    authorize_login = fields.Char(string='API Login Id', required_if_provider='authorize', groups='base.group_user')
    authorize_transaction_key = fields.Char(string='API Transaction Key', required_if_provider='authorize', groups='base.group_user')

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirerAuthorize, self)._get_feature_support()
        res['authorize'].append('authorize')
        res['tokenize'].append('authorize')
        return res

    def _get_authorize_urls(self, environment):
        """ Authorize URLs """
        if environment == 'prod':
            return {'authorize_form_url': 'https://secure2.authorize.net/gateway/transact.dll'}
        else:
            return {'authorize_form_url': 'https://test.authorize.net/gateway/transact.dll'}

    def _authorize_generate_hashing(self, values):
        data = '^'.join([
            values['x_login'],
            values['x_fp_sequence'],
            values['x_fp_timestamp'],
            values['x_amount'],
            values['x_currency_code']])
        return hmac.new(values['x_trans_key'].encode('utf-8'), data.encode('utf-8'), hashlib.md5).hexdigest()

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
            'x_type': 'AUTH_CAPTURE' if not self.capture_manually else 'AUTH_ONLY',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (self.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': urls.url_join(base_url, AuthorizeController._return_url),
            'x_cancel_url': urls.url_join(base_url, AuthorizeController._cancel_url),
            'x_currency_code': values['currency'] and values['currency'].name or '',
            'address': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').name or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'phone': values.get('partner_phone'),
            'state': values.get('partner_state') and values['partner_state'].code or '',
            'billing_address': values.get('billing_partner_address'),
            'billing_city': values.get('billing_partner_city'),
            'billing_country': values.get('billing_partner_country') and values.get('billing_partner_country').name or '',
            'billing_email': values.get('billing_partner_email'),
            'billing_zip_code': values.get('billing_partner_zip'),
            'billing_first_name': values.get('billing_partner_first_name'),
            'billing_last_name': values.get('billing_partner_last_name'),
            'billing_phone': values.get('billing_partner_phone'),
            'billing_state': values.get('billing_partner_state') and values['billing_partner_state'].code or '',
        }
        temp_authorize_tx_values['returndata'] = authorize_tx_values.pop('return_url', '')
        temp_authorize_tx_values['x_fp_hash'] = self._authorize_generate_hashing(temp_authorize_tx_values)
        temp_authorize_tx_values.pop('x_trans_key') # We remove this value since it is secret and isn't needed on the form
        authorize_tx_values.update(temp_authorize_tx_values)
        return authorize_tx_values

    @api.multi
    def authorize_get_form_action_url(self):
        self.ensure_one()
        return self._get_authorize_urls(self.environment)['authorize_form_url']

    @api.model
    def authorize_s2s_form_process(self, data):
        values = {
            'cc_number': data.get('cc_number'),
            'cc_holder_name': data.get('cc_holder_name'),
            'cc_expiry': data.get('cc_expiry'),
            'cc_cvc': data.get('cc_cvc'),
            'cc_brand': data.get('cc_brand'),
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id'))
        }
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        return PaymentMethod

    @api.multi
    def authorize_s2s_form_validate(self, data):
        error = dict()
        mandatory_fields = ["cc_number", "cc_cvc", "cc_holder_name", "cc_expiry", "cc_brand"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        if data['cc_expiry'] and datetime.now().strftime('%y%m') > datetime.strptime(data['cc_expiry'], '%m / %y').strftime('%y%m'):
            return False
        return False if error else True

    @api.multi
    def authorize_test_credentials(self):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        return transaction.test_authenticate()

class TxAuthorize(models.Model):
    _inherit = 'payment.transaction'

    _authorize_valid_tx_status = 1
    _authorize_pending_tx_status = 4
    _authorize_cancel_tx_status = 2

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def create(self, vals):
        # The reference is used in the Authorize form to fill a field (invoiceNumber) which is
        # limited to 20 characters. We truncate the reference now, since it will be reused at
        # payment validation to find back the transaction.
        if 'reference' in vals and 'acquirer_id' in vals:
            acquier = self.env['payment.acquirer'].browse(vals['acquirer_id'])
            if acquier.provider == 'authorize':
                vals['reference'] = vals.get('reference', '')[:20]
        return super(TxAuthorize, self).create(vals)

    @api.model
    def _authorize_form_get_tx_from_data(self, data):
        """ Given a data dict coming from authorize, verify it and find the related
        transaction record. """
        reference, trans_id, fingerprint = data.get('x_invoice_num'), data.get('x_trans_id'), data.get('x_MD5_Hash')
        if not reference or not trans_id or not fingerprint:
            error_msg = _('Authorize: received data with missing reference (%s) or trans_id (%s) or fingerprint (%s)') % (reference, trans_id, fingerprint)
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Authorize: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    @api.multi
    def _authorize_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('x_trans_id') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('x_trans_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('x_amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('x_amount'), '%.2f' % self.amount))
        return invalid_parameters

    @api.multi
    def _authorize_form_validate(self, data):
        if self.state in ['done', 'refunded']:
            _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = int(data.get('x_response_code', '0'))
        if status_code == self._authorize_valid_tx_status:
            if data.get('x_type').lower() in ['auth_capture', 'prior_auth_capture']:
                self.write({
                    'state': 'done',
                    'acquirer_reference': data.get('x_trans_id'),
                    'date_validate': fields.Datetime.now(),
                })
            elif data.get('x_type').lower() in ['auth_only']:
                self.write({
                    'state': 'authorized',
                    'acquirer_reference': data.get('x_trans_id'),
                })
            if self.partner_id and not self.payment_token_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always'):
                transaction = AuthorizeAPI(self.acquirer_id)
                res = transaction.create_customer_profile_from_tx(self.partner_id, self.acquirer_reference)
                token_id = self.env['payment.token'].create({
                    'authorize_profile': res.get('profile_id'),
                    'name': res.get('name'),
                    'acquirer_ref': res.get('payment_profile_id'),
                    'acquirer_id': self.acquirer_id.id,
                    'partner_id': self.partner_id.id,
                })
                self.payment_token_id = token_id

            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        elif status_code == self._authorize_pending_tx_status:
            self.write({
                'state': 'pending',
                'acquirer_reference': data.get('x_trans_id'),
            })
            return True
        elif status_code == self._authorize_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': data.get('x_trans_id'),
                'state_message': data.get('x_response_reason_text'),
            })
            return True
        else:
            error = data.get('x_response_reason_text')
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('x_trans_id'),
            })
            return False

    @api.multi
    def authorize_s2s_do_transaction(self, **data):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        if not self.acquirer_id.capture_manually:
            res = transaction.auth_and_capture(self.payment_token_id, self.amount, self.reference)
        else:
            res = transaction.authorize(self.payment_token_id, self.amount, self.reference)
        return self._authorize_s2s_validate_tree(res)

    @api.multi
    def authorize_s2s_do_refund(self):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        self.state = 'refunding'
        if self.type == 'validation':
            res = transaction.void(self.acquirer_reference)
        else:
            res = transaction.credit(self.payment_token_id, self.amount, self.acquirer_reference)
        return self._authorize_s2s_validate_tree(res)

    @api.multi
    def authorize_s2s_capture_transaction(self):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        tree = transaction.capture(self.acquirer_reference or '', self.amount)
        return self._authorize_s2s_validate_tree(tree)

    @api.multi
    def authorize_s2s_void_transaction(self):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        tree = transaction.void(self.acquirer_reference or '')
        return self._authorize_s2s_validate_tree(tree)

    @api.multi
    def _authorize_s2s_validate_tree(self, tree):
        return self._authorize_s2s_validate(tree)

    @api.multi
    def _authorize_s2s_validate(self, tree):
        if self.state in ['done', 'refunded']:
            _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = int(tree.get('x_response_code', '0'))
        if status_code == self._authorize_valid_tx_status:
            if tree.get('x_type').lower() in ['auth_capture', 'prior_auth_capture']:
                init_state = self.state
                self.write({
                    'state': 'done',
                    'acquirer_reference': tree.get('x_trans_id'),
                    'date_validate': fields.Datetime.now(),
                })
                if init_state != 'authorized':
                    self.execute_callback()

                if self.payment_token_id:
                    self.payment_token_id.verified = True

            if tree.get('x_type').lower() == 'auth_only':
                self.write({
                    'state': 'authorized',
                    'acquirer_reference': tree.get('x_trans_id'),
                })
                self.execute_callback()
            if tree.get('x_type').lower() == 'void':
                if self.type == 'validation' and self.state == 'refunding':
                    self.write({
                        'state': 'refunded',
                    })
                else:
                    self.write({
                        'state': 'cancel',
                    })
            return True
        elif status_code == self._authorize_pending_tx_status:
            new_state = 'refunding' if self.state == 'refunding' else 'pending'
            self.write({
                'state': new_state,
                'acquirer_reference': tree.get('x_trans_id'),
            })
            return True
        elif status_code == self._authorize_cancel_tx_status:
            self.write({
                'state': 'cancel',
                'acquirer_reference': tree.get('x_trans_id'),
            })
            return True
        else:
            error = tree.get('x_response_reason_text')
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': tree.get('x_trans_id'),
            })
            return False


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    authorize_profile = fields.Char(string='Authorize.net Profile ID', help='This contains the unique reference '
                                    'for this partner/payment token combination in the Authorize.net backend')
    provider = fields.Selection(string='Provider', related='acquirer_id.provider')
    save_token = fields.Selection(string='Save Cards', related='acquirer_id.save_token')

    @api.model
    def authorize_create(self, values):
        if values.get('cc_number'):
            values['cc_number'] = values['cc_number'].replace(' ', '')
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
            expiry = str(values['cc_expiry'][:2]) + str(values['cc_expiry'][-2:])
            partner = self.env['res.partner'].browse(values['partner_id'])
            transaction = AuthorizeAPI(acquirer)
            res = transaction.create_customer_profile(partner, values['cc_number'], expiry, values['cc_cvc'])
            if res.get('profile_id') and res.get('payment_profile_id'):
                return {
                    'authorize_profile': res.get('profile_id'),
                    'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name']),
                    'acquirer_ref': res.get('payment_profile_id'),
                }
            else:
                raise ValidationError(_('The Customer Profile creation in Authorize.NET failed.'))
        else:
            return values
