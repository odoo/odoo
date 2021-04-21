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
    def _get_nelo_urls(self):
        if self.state == 'enabled': #prod
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
        payload = json.dumps({
        "order": {
            "id": values['reference'],
            "totalAmount": {
                "amount": values['amount']*100.0, # in cents
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
        "redirectConfirmUrl": urls.url_join(self.get_base_url(), NeloController._confirm_url),
        "redirectCancelUrl": urls.url_join(self.get_base_url(), NeloController._cancel_url)
        })
        headers = {
            'Authorization': 'Bearer %s' % (self.nelo_merchant_secret),
            'Content-Type': 'application/json'
        }
        _logger.info('Payload\n %s', pprint.pformat(payload))  # debug

        url = '%s/checkout' % (self._get_nelo_urls()['rest_url'])
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        self._nelo_redirect_url = response.json()['redirectUrl']

    def nelo_form_generate_values(self, values):
        self._set_redirect_url(values)
        return values

    def nelo_get_form_action_url(self):
        self.ensure_one()
        return self._get_nelo_urls()['web_url']


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _nelo_form_get_tx_from_data(self, data):
        reference = data.get('reference')

        if not reference:
            _logger.info('Nelo: received data with missing reference/order_id (%s)' % (reference))
            raise ValidationError(_('Nelo: received data with missing reference (%s)') % (reference))

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

    def _nelo_form_validate(self, data):
        if self.state in ['done']:
            _logger.info('Nelo: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        payload = {
            'acquirer_reference': data.get('reference'),
            'date': fields.Datetime.now()
        }
        _logger.info('Validated Nelo payment for tx %s: set as done' % (self.reference))
        self._set_transaction_done()
        self.write(payload)
        self.execute_callback()
        return True
       
