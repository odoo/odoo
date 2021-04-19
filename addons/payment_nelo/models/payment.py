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

    nelo_merchant_secret = fields.Char(
        string='Merchant Secret', required_if_provider='nelo', groups='base.group_user',
        help='The Merchant Secret is used to ensure communications with Nelo.')

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
            'Authorization': 'Bearer %s' % (self.nelo_merchant_secret),
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

    def nelo_form_generate_values(self, values):
        self._set_redirect_url(values)
        return values

    def nelo_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_nelo_urls(environment)['web_url']


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _nelo_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('reference'), data.get('trade_no')
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
