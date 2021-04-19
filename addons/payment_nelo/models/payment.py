# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from hashlib import md5
from werkzeug import urls
import requests

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.payment_nelo.controllers.main import NeloController
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('nelo', 'Nelo')
    ], ondelete={'nelo': 'set default'})
    _nelo_redirect_url = fields.Char('', invisible = True)

    nelo_payment_method = fields.Selection([
        ('express_checkout', 'Express Checkout (only for Chinese Merchant)'),
        ('standard_checkout', 'Cross-border'),
    ], string='Account', default='express_checkout',
        help="  * Cross-border: For the Overseas seller \n  * Express Checkout: For the Chinese Seller")
    nelo_merchant_partner_id = fields.Char(
        string='Merchant Partner ID', required_if_provider='nelo', groups='base.group_user',
        help='The Merchant Partner ID is used to ensure communications coming from Nelo are valid and secured.')
    nelo_md5_signature_key = fields.Char(
        string='MD5 Signature Key', required_if_provider='nelo', groups='base.group_user',
        help="The MD5 private key is the 32-byte string which is composed of English letters and numbers.")
    nelo_seller_email = fields.Char(string='Nelo Seller Email', groups='base.group_user')

    @api.model
    def _get_nelo_urls(self, environment):
        if environment == 'prod':
            return {
                'web_url': self._nelo_redirect_url,
                'rest_url': 'https://api-v2-dev.nelo.co/v1'
            }
        else:
            return {
                'web_url': self._nelo_redirect_url,
                'rest_url': 'https://api-v2-dev.nelo.co/v1'
            }

    def _set_redirect_url(self, values):
        base_url = self.get_base_url()

        payload = json.dumps({
        "order": {
            "id": values['reference'],
            "totalAmount": {
                "amount": values['amount'],
                "currencyCode": 'MXN'
            }
        },
        "customer": {
            "phoneNumber": {
                "number": values['partner_phone'],
                "countryIso2": "MX"
            },
            "firstName": values['partner_first_name'],
            "maternalLastName": '',
            "paternalLastName": values['partner_last_name'],
            "email": values['partner_email'],
            "address": {
                "addressMX": {
                    "buildingNumber": '',
                    "street": values['partner_address'],
                    "interiorNumber": '',
                    "city": values['partner_city'],
                    "delegation": "Cuauhtemoc",
                    "state": values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
                    "colony": 'Juarez',
                    "postalCode": values['partner_zip']
                },
                "countryIso2": "MX"
            }
        },
        "redirectConfirmUrl": urls.url_join(base_url, NeloController._confirm_url),
        "redirectCancelUrl": urls.url_join(base_url, NeloController._cancel_url)
        })

        _logger.info('Payload\n %s', pprint.pformat(payload))  # debug
        

        headers = {
            'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJkYmZjMzgxYy1jZjNiLTQ0NGUtYTRlNS03YTI0NGM5YjgzNjMiLCJpc3MiOiJuZWxvLmNvIiwiYWN0aW9uIjoiTUVSQ0hBTlRfQVBJIiwiaWF0IjoxNjE3ODU2NjExfQ.YKsV3CUuReU3gXq6UCbUcu5hLG7iyT1TvakNp7kWk-Nibwz835-Suuv3xTtqsAZ0ML8vjUjfHz_DKqfaD4S2HQ',
            'Content-Type': 'application/json'
        }
        _logger.info('Headers\n %s', pprint.pformat(headers))  # debug

        environment = 'prod' if self.state == 'enabled' else 'test'
        url = '%s/checkout' % (self._get_nelo_urls(environment)['rest_url'])
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        jsonResp = response.json()
        _logger.info('Response\n %s \n', pprint.pformat(jsonResp))  # debug
        self._nelo_redirect_url = jsonResp['redirectUrl']

    def _build_sign(self, val):
        # Rearrange parameters in the data set alphabetically
        data_to_sign = sorted(val.items())
        # Exclude parameters that should not be signed
        data_to_sign = ["{}={}".format(k, v) for k, v in data_to_sign if k not in ['sign', 'sign_type', 'reference']]
        # And connect rearranged parameters with &
        data_string = '&'.join(data_to_sign)
        data_string += self.nelo_md5_signature_key
        return md5(data_string.encode('utf-8')).hexdigest()

    def nelo_form_generate_values(self, values):
        self._set_redirect_url(values)
        return values

    def nelo_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_nelo_urls(environment)['web_url']


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_nelo_configuration(self, vals):
        acquirer_id = int(vals.get('acquirer_id'))
        acquirer = self.env['payment.acquirer'].sudo().browse(acquirer_id)
        if acquirer and acquirer.provider == 'nelo' and acquirer.nelo_payment_method == 'express_checkout':
            currency_id = int(vals.get('currency_id'))
            if currency_id:
                currency = self.env['res.currency'].sudo().browse(currency_id)
                if currency and currency.name != 'CNY':
                    _logger.info("Only CNY currency is allowed for Nelo Express Checkout")
                    raise ValidationError(_("""
                        Only transactions in Chinese Yuan (CNY) are allowed for Nelo Express Checkout.\n
                        If you wish to use another currency than CNY for your transactions, switch your
                        configuration to a Cross-border account on the Nelo payment acquirer in Odoo.
                    """))
        return True

    def write(self, vals):
        if vals.get('currency_id') or vals.get('acquirer_id'):
            for payment in self:
                check_vals = {
                    'acquirer_id': vals.get('acquirer_id', payment.acquirer_id.id),
                    'currency_id': vals.get('currency_id', payment.currency_id.id)
                }
                payment._check_nelo_configuration(check_vals)
        return super(PaymentTransaction, self).write(vals)

    @api.model
    def create(self, vals):
        self._check_nelo_configuration(vals)
        return super(PaymentTransaction, self).create(vals)

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _nelo_form_get_tx_from_data(self, data):
        reference, txn_id, sign = data.get('reference'), data.get('trade_no'), data.get('sign')
        if not reference or not txn_id:
            _logger.info('Nelo: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id))
            raise ValidationError(_('Nelo: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id))

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = _('Nelo: received data for reference %s') % (reference)
            logger_msg = 'Nelo: received data for reference %s' % (reference)
            if not txs:
                error_msg += _('; no order found')
                logger_msg += '; no order found'
            else:
                error_msg += _('; multiple order found')
                logger_msg += '; multiple order found'
            _logger.info(logger_msg)
            raise ValidationError(error_msg)

        # verify sign
        sign_check = txs.acquirer_id._build_sign(data)
        if sign != sign_check:
            _logger.info('Nelo: invalid sign, received %s, computed %s, for data %s' % (sign, sign_check, data))
            raise ValidationError(_('Nelo: invalid sign, received %s, computed %s, for data %s') % (sign, sign_check, data))

        return txs

    def _nelo_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if float_compare(float(data.get('total_fee', '0.0')), (self.amount + self.fees), 2) != 0:
            invalid_parameters.append(('total_fee', data.get('total_fee'), '%.2f' % (self.amount + self.fees)))  # mc_gross is amount + fees
        if self.acquirer_id.nelo_payment_method == 'standard_checkout':
            if data.get('currency') != self.currency_id.name:
                invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))
        else:
            if data.get('seller_email') != self.acquirer_id.nelo_seller_email:
                invalid_parameters.append(('seller_email', data.get('seller_email'), self.acquirer_id.nelo_seller_email))
        return invalid_parameters

    def _nelo_form_validate(self, data):
        if self.state in ['done']:
            _logger.info('Nelo: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = data.get('trade_status')
        res = {
            'acquirer_reference': data.get('trade_no'),
        }
        if status in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
            _logger.info('Validated Nelo payment for tx %s: set as done' % (self.reference))
            date_validate = fields.Datetime.now()
            res.update(date=date_validate)
            self._set_transaction_done()
            self.write(res)
            self.execute_callback()
            return True
        elif status == 'TRADE_CLOSED':
            _logger.info('Received notification for Nelo payment %s: set as Canceled' % (self.reference))
            res.update(state_message=data.get('close_reason', ''))
            self._set_transaction_cancel()
            return self.write(res)
        else:
            error = 'Received unrecognized status for Nelo payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state_message=error)
            self._set_transaction_error()
            return self.write(res)
