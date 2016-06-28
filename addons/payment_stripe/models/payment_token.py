# coding: utf-8

import requests

from odoo import api, models
from odoo.exceptions import UserError
from . import payment_acquirer as pa


class PaymentTokenStripe(models.Model):
    _inherit = 'payment.token'

    @api.model
    def stripe_create(self, values):
        res = None
        payment_acquirer = self.env['payment.acquirer'].browse(values.get('acquirer_id'))
        url_token = 'https://%s/tokens' % payment_acquirer._get_stripe_api_url()
        url_customer = 'https://%s/customers' % payment_acquirer._get_stripe_api_url()
        if values['cc_number']:
            payment_params = {
                'card[number]': values['cc_number'].replace(' ', ''),
                'card[exp_month]': str(values['cc_expiry'][:2]),
                'card[exp_year]': str(values['cc_expiry'][-2:]),
                'card[cvc]': values['cvc'],
            }
            r = requests.post(url_token,
                              auth=(payment_acquirer.stripe_secret_key, ''),
                              params=payment_params,
                              headers=pa.STRIPE_HEADERS)
            token = r.json()
            if token.get('id'):
                customer_params = {
                    'source': token['id']
                }
                r = requests.post(url_customer,
                                  auth=(payment_acquirer.stripe_secret_key, ''),
                                  params=customer_params,
                                  headers=pa.STRIPE_HEADERS)
                customer = r.json()
                res = {
                    'acquirer_ref': customer['id'],
                    'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name'])
                }
            elif token.get('error'):
                raise UserError(token['error']['message'])

        # pop credit card info to info sent to create
        for field_name in ["cc_number", "cvc", "cc_holder_name", "cc_expiry", "cc_brand"]:
            values.pop(field_name)
        return res
