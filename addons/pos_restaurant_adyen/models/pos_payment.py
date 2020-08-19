# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from odoo import models

TIMEOUT = 10


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    def _update_payment_line_for_tip(self, tip_amount):
        """Capture the correct amount when a tip is set."""
        res = super(PosPayment, self)._update_payment_line_for_tip(tip_amount)
        if self.payment_method_id.use_payment_terminal == 'adyen':
            self._adyen_capture_tip(True)
        return res

    def _adyen_capture_tip(self, adjust_authorisation=False):
        endpoint = 'https://pal-live.adyen.com/pal/servlet/Payment/v52/'
        if self.payment_method_id.adyen_test_mode:
            endpoint = 'https://pal-test.adyen.com/pal/servlet/Payment/v52/'

        headers = {
            'x-api-key': self.payment_method_id.adyen_api_key,
            'Content-Type': 'application/json'
        }

        data = {
            'originalReference': self.transaction_id,
            'modificationAmount': {
                'value': int(self.amount * 10**self.currency_id.decimal_places),
                'currency': self.currency_id.name,
            },
            'merchantAccount': self.payment_method_id.adyen_merchant_account,
        }

        if adjust_authorisation:
            endpoint += 'adjustAuthorisation'
            data['additionalData'] = {
                'industryUsage':'DelayedCharge'
            }
        else:
            endpoint += 'capture'

        req = requests.post(endpoint, data=json.dumps(data), headers=headers, timeout=TIMEOUT)

        if not req.ok:
            raise Exception('An error occured while capturing the payment')
