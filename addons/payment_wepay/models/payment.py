# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import requests

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from odoo.addons.payment_wepay.controllers.main import WepayController
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('wepay', 'WePay')])
    wepay_account_id = fields.Char(string='Wepay Account ID', required_if_provider='wepay', groups='base.group_user', help="This is the ID of the payment account where you can collect money.")
    wepay_client_id = fields.Char(string='Wepay Client ID', required_if_provider='wepay', groups='base.group_user', help="This is the ID of your API application")
    wepay_access_token = fields.Char(string='Wepay Access Token', required_if_provider='wepay', groups='base.group_user', help="This is the access_token that grants this app permission to do things on behalf of you")

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirer, self)._get_feature_support()
        res['fees'].append('wepay')
        res['tokenize'].append('wepay')
        return res

    @api.model
    def _get_wepay_urls(self, environment):
        """ wepay URLS """
        if environment == 'prod':
            return {
                'checkout_create': 'https://wepayapi.com/v2/checkout/create',
                'checkout': 'https://wepayapi.com/v2/checkout/',
                'checkout_refund': 'https://wepayapi.com/v2/checkout/refund',
                'credict_card_create': 'https://wepayapi.com/v2/credit_card/create',
            }
        return {
            'checkout_create': 'https://stage.wepayapi.com/v2/checkout/create',
            'checkout': 'https://stage.wepayapi.com/v2/checkout/',
            'checkout_refund': 'https://stage.wepayapi.com/v2/checkout/refund',
            'credict_card_create': 'https://stage.wepayapi.com/v2/credit_card/create',
        }

    @api.multi
    def wepay_compute_fees(self, amount, currency_id, country_id):
        """ Compute wepay fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        fees = 0.0
        if self.fees_active:
            country = self.env['res.country'].browse(country_id)
            if country and self.company_id.country_id.id == country.id:
                percentage = self.fees_dom_var
                fixed = self.fees_dom_fixed
            else:
                percentage = self.fees_int_var
                fixed = self.fees_int_fixed
            fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    @api.multi
    def get_wepay_header(self):
        return {
            'content-type': "application/json",
            'cache-control': "no-cache",
            'authorization': "Bearer %s" % self.wepay_access_token
        }

    @api.multi
    def _get_wepay_getway(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        tx = self.env['payment.transaction'].search([('reference', '=', values.get('reference'))])
        val = json.dumps({
            "account_id": self.wepay_account_id,
            "amount": values.get('amount'),
            "type": "service" if all(var == "service" for var in tx.sale_order_id.order_line.mapped('product_id.type')) else "goods",
            "currency": values.get('currency').name,
            "short_description": values.get('reference'),
            "callback_uri": urls.url_join(base_url, WepayController._notify_url),
            "reference_id": values.get('reference'),
            "hosted_checkout": {
                "redirect_uri": urls.url_join(base_url, WepayController._return_url) + "?redirect_url=" + str(values.get('return_url')),
            },
            'fee': {
                'app_fee': values['fees'],
            }
        })
        response = requests.post(self.wepay_get_form_action_url()['checkout_create'], data=val, headers=self.get_wepay_header())
        vals = json.loads(response.text)
        _logger.info(pprint.pformat(vals))
        return vals

    @api.multi
    def wepay_form_generate_values(self, values):
        val = self._get_wepay_getway(values)
        try:
            values.update({
                'checkout_getway': val['hosted_checkout']['checkout_uri'],
            })
        except KeyError:
            raise UserError(val['error_description'])
        return values

    @api.multi
    def wepay_get_form_action_url(self):
        return self._get_wepay_urls(self.environment)

    @api.model
    def wepay_s2s_form_process(self, data):
        payment_token = self.env['payment.token'].sudo().create({
            'cc_number': data['cc_number'],
            'cc_holder_name': data['cc_holder_name'],
            'cc_expiry': data['cc_expiry'],
            'cc_brand': data['cc_brand'],
            'cvc': data['cvc'],
            'acquirer_id': int(data['acquirer_id']),
            'partner_id': int(data['partner_id']),
        })
        return payment_token

    @api.multi
    def wepay_s2s_form_validate(self, data):
        self.ensure_one()

        # mandatory fields
        for field_name in ["cc_number", "cvc", "cc_holder_name", "cc_expiry", 'cc_brand']:
            if not data.get(field_name):
                return False
        return True


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.multi
    def wepay_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        result = self._create_wepay_charge()
        return self._wepay_form_validate(result)

    def _create_wepay_charge(self):
        val = json.dumps({
            "account_id": self.acquirer_id.wepay_account_id,
            "amount": self.amount,
            "currency": self.currency_id.name,
            "short_description": "Payment From Odoo",
            "type": "goods",
            "reference_id": self.reference,
            "payment_method": {
                'type': 'credit_card',
                'credit_card': {
                    'id': self.payment_token_id.acquirer_ref
                }
            },
            'fee': {
                'app_fee': self.fees,
            }
        })

        response = requests.post(self.acquirer_id.wepay_get_form_action_url()['checkout_create'], data=val, headers=self.acquirer_id.get_wepay_header())
        res = response.json()
        _logger.info('_create_wepay_charge: Values received:\n%s', pprint.pformat(res))
        return res

    @api.model
    def _wepay_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('reference_id'), data.get('checkout_id')
        if not reference or not txn_id:
            error_msg = _('WePay: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'WePay: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs

    @api.multi
    def _wepay_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        # check what is buyed
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))  # mc_gross is amount + fees
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))
        if 'app_fee' in data.get('fee') and float_compare(float(data.get('fee').get('app_fee')), self.fees, 2) != 0:
            invalid_parameters.append(('fee', data.get('fee').get('app_fee'), self.fees))
        # check seller
        if data.get('account_id') and self.acquirer_id.wepay_account_id and data.get('account_id') != int(self.acquirer_id.wepay_account_id):
            invalid_parameters.append(('account_id', data.get('account_id'), self.acquirer_id.wepay_account_id))

        return invalid_parameters

    @api.multi
    def _create_wepay_refund(self):
        val = json.dumps({
            "checkout_id": self.acquirer_reference,
            "refund_reason": 'Reason',
        })

        response = requests.post(self.acquirer_id._get_wepay_urls(self.acquirer_id.environment)['checkout_refund'], data=val, headers=self.acquirer_id.get_wepay_header())
        res = response.json()
        _logger.info('_create_wepay_refund: Values received:\n%s', pprint.pformat(res))
        return res

    @api.multi
    def wepay_s2s_do_refund(self, **kwargs):
        self.ensure_one()
        self.state = 'refunding'
        result = self._create_wepay_refund()
        return self._wepay_form_validate(result)

    @api.multi
    def _wepay_form_validate(self, data):
        self.ensure_one()
        if self.state not in ('draft', 'pending', 'refunding'):
            _logger.info('Wepay: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        try:
            status = data.get('state')
        except KeyError:
            raise UserError(data['error_description'])
        if status in ['authorized', 'captured', 'refunded']:
            new_state = 'refunded' if self.state == 'refunding' else 'done'
            _logger.info('Validated Wepay payment for tx %s: set as %s' % (self.reference, new_state))
            self.write({
                'state': new_state,
                'date_validate': fields.datetime.now(),
                'acquirer_reference': data.get('checkout_id'),
            })
            self.execute_callback()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        elif status == 'released':
            _logger.info('Received notification for wepay payment %s: set as pending' % (self.reference))
            self.write({
                'state': 'pending',
                'acquirer_reference': data.get('checkout_id'),
            })
            self.execute_callback()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        elif status in ['cancelled', 'falled', 'failed']:
            _logger.info('Received notification for wepay payment %s: set as cancel' % (self.reference))
            self.write({
                'state': 'cancel',
                'acquirer_reference': data.get('checkout_id'),
            })
            return True
        else:
            error = 'Received unrecognized status for Wepay payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            self.sudo().write({
                'state': 'error',
                'state_message': error,
                'acquirer_reference': data.get('checkout_id'),
                'date_validate': fields.datetime.now(),
            })
            return False


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    @api.model
    def wepay_create(self, values):
        res = {}
        payment_acquirer = self.env['payment.acquirer'].browse(values.get('acquirer_id'))
        partner = self.env['res.partner'].browse(values.get('partner_id'))
        missing_field = [partner._fields[field].string for field in ['country_id', 'zip'] if not partner[field]]
        if missing_field:
            raise ValidationError({'missing_field': missing_field})
        if values.get('cc_number'):
            payment_params = json.dumps({
                'client_id': int(payment_acquirer.wepay_client_id),
                'user_name': values.get('cc_holder_name'),
                'email': partner.email,
                'cc_number': values.get('cc_number').replace(' ', ''),
                'cvv': values.get('cvc'),
                'expiration_month': int(values.get('cc_expiry')[:2]),
                'expiration_year': int(values.get('cc_expiry')[-2:]),
                'address': {
                    "country": partner.country_id.code,
                    "postal_code": partner.zip
                }
            })
            response = requests.post(payment_acquirer.wepay_get_form_action_url()['credict_card_create'], data=payment_params, headers=payment_acquirer.get_wepay_header())
            token = response.json()
            _logger.info('_create_credit_card: Values received:\n%s', pprint.pformat(token))
            try:
                res = {
                    'acquirer_ref': token['credit_card_id'],
                    'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name'])
                }
            except KeyError:
                raise UserError(token.get('error_description'))

        # pop credit card info to info sent to create
        for field_name in ["cc_number", "cvc", "cc_holder_name", "cc_expiry", "cc_brand"]:
            values.pop(field_name, None)
        return res
