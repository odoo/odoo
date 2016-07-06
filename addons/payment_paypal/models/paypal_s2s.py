# -*- coding: utf-'8' "-*-"

import base64
import json
import logging
import time
import urllib
import urllib2

from odoo import api, models, _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class AcquirerPaypalS2s(models.Model):
    _inherit = 'payment.acquirer'

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    @api.model
    def paypal_s2s_form_process(self, data):
        values = {
            'cc_holder_name': data.get('cc_holder_name'),
            'cc_number': data.get('cc_number'),
            'cc_expiry': data.get('cc_expiry'),
            'cc_cvv': data.get('cc_cvv'),
            'cc_brand': data.get('cc_brand'),
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id'))
        }
        payment_method = self.env['payment.method'].sudo().create(values)
        return payment_method.id

    @api.multi
    def _paypal_s2s_get_access_token(self):
        path = '/v1/oauth2/token'
        token_url = self._get_paypal_urls(self.environment)['paypal_rest_url'] + path
        credentials = "%s:%s" % (self.paypal_client_id, self.paypal_client_secret)
        encode_credential = base64.b64encode(credentials)
        token_headers = {
            'Authorization': ('Basic %s' % encode_credential),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        token_params = {
            'grant_type': 'client_credentials',
        }
        token_request = urllib2.Request(token_url, urllib.urlencode(token_params), token_headers)
        token_response = urllib2.urlopen(token_request)
        token_result = json.loads(token_response.read())
        token_response.close()
        return token_result.get('access_token')

    @api.multi
    def paypal_s2s_form_validate(self, data):
        self.ensure_one()

        # mandatory fields
        for field_name in ["cc_number", "cc_cvv", "cc_holder_name", "cc_expiry", "cc_brand"]:
            if not data.get(field_name):
                return False
        return True


class TxPaypalS2s(models.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # SERVER2SERVER RELATED METHODS
    # --------------------------------------------------

    def _paypal_try_url(self, request, tries=3):
        done, res = False, None
        while (not done and tries):
            try:
                res = urllib2.urlopen(request)
                done = True
            except urllib2.HTTPError as e:
                res = e.read()
                e.close()
                if tries and res and json.loads(res)['name'] == 'INTERNAL_SERVICE_ERROR':
                    _logger.warning('Failed contacting Paypal, retrying (%s remaining)' % tries)
            tries = tries - 1
        if not res:
            pass
        result = json.loads(res.read())
        res.close()
        return result

    @api.multi
    def paypal_s2s_do_transaction(self, **kwargs):
        self.ensure_one()
        if not self.payment_method_id:
            raise UserWarning(_('Credit/Debit card has been not added in your account.'))

        path = '/v1/payments/payment'
        payment_url = self.env['payment.acquirer']._get_paypal_urls(self.acquirer_id.environment)['paypal_rest_url'] + path

        access_token = self.acquirer_id._paypal_s2s_get_access_token()
        payment_headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json'
        }

        data = {
            'intent': 'sale',
            'payer': {
                'payment_method': 'credit_card',
                'funding_instruments': [{
                    'credit_card_token': {
                        'credit_card_id': str(self.payment_method_id.acquirer_ref),
                        'payer_id': str(self.payment_method_id.partner_id.id)
                    }
                }]
            },
            'transactions': [{
                'amount': {
                    'total': "{:.2f}".format(self.amount),
                    'currency': str(self.currency_id.name),
                },
                'description': str(self.display_name)
            }]
        }
        payment_result = dict()
        try:
            payment_request = urllib2.Request(payment_url,
                                              json.dumps(data),
                                              payment_headers)
            payment_result = self._paypal_try_url(payment_request, tries=3)

        except Exception, e:
            _logger.exception('PayPal payment request failed: %s' % e)
            raise UserWarning(_('PayPal payment request failed.'))

        return self._paypal_s2s_validate_tree(payment_result)

    @api.multi
    def _paypal_s2s_validate_tree(self, tree):
        self.ensure_one()

        if self.state not in ('draft', 'pending'):
            _logger.info('Paypal: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        response = tree.get('state')
        if response == 'approved':
            state_msg = 'Received response for Paypal payment tx %s: '\
                        'set as %s' % (self.reference, response)
            _logger.info(state_msg)
            self.write({
                'state': 'done',
                'acquirer_reference': tree['id'],
                'state_message': _(state_msg),
                'date_validate': tree['update_time']
            })
            if self.callback_eval:
                safe_eval(self.callback_eval, {'self': self})
            return True
        elif response in ['pending', 'expired', 'failed', 'canceled']:
            if response == 'pending':
                time.sleep(500)
            response = 'cancel' if response == 'canceled' else response
            state_msg = 'Received response for Paypal payment '\
                        'transaction %s: set as %s' % (self.reference, response)
            _logger.info(state_msg)
            self.write({
                'state': response,
                'acquirer_reference': tree['id'],
                'state_message': _(state_msg),
            })
            return True
        else:
            state_msg = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (self.reference, response)

            _logger.info(state_msg)
            self.write({
                'state': 'error',
                'state_message': _(state_msg),
            })
            return True


class PaymentMethodPaypal(models.Model):
    _inherit = 'payment.method'

    @api.model
    def paypal_create(self, values):
        acquirer = self.env['payment.acquirer'].browse(int(values.get('acquirer_id')))

        access_token = acquirer._paypal_s2s_get_access_token()
        path = '/v1/vault/credit-card'
        vault_url = self.env['payment.acquirer']._get_paypal_urls(acquirer.environment)['paypal_rest_url'] + path

        vault_headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json'
        }
        vault_params = {
            'payer_id': values['partner_id'],
            'type': values['cc_brand'],
            'number': values['cc_number'].replace(' ', ''),
            'expire_month': str(values['cc_expiry'][:2]),
            'expire_year': '20' + str(values['cc_expiry'][-2:]),
            'cvv2': values['cc_cvv'][:3],
        }
        vault_request = urllib2.Request(vault_url, json.dumps(vault_params), vault_headers)
        vault_response = urllib2.urlopen(vault_request)
        vault_result = json.loads(vault_response.read())
        vault_response.close()

        if not vault_result['state'] == 'ok':
            _logger.error('Paypal Vault: error when storing credit card %s: %s' % (values['cc_number'][-4:], vault_result['state']))
            raise Exception(_('Store credit card details on PayPal Vault has been failed'))

        return {
            'acquirer_ref': vault_result['id'],
            'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name'])
        }
