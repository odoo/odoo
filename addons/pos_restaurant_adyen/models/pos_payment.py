# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from odoo import models

TIMEOUT = 10


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    def _update_payment_line_for_tip(self, tip_amount):
        """Capture the payment when a tip is set."""
        res = super(PosPayment, self)._update_payment_line_for_tip(tip_amount)
        if self.payment_method_id.use_payment_terminal == 'adyen':
            self._adyen_capture()
        return res

    def _adyen_capture(self):
        data = {
            'originalReference': self.transaction_id,
            'modificationAmount': {
                'value': int(self.amount * 10**self.currency_id.decimal_places),
                'currency': self.currency_id.name,
            },
            'merchantAccount': self.payment_method_id.adyen_merchant_account,
        }

        return self.payment_method_id.proxy_adyen_request(data, 'capture')
