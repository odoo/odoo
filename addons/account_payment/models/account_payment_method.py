# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        for provider, _desc in self.env['payment.acquirer']._fields['provider'].selection:
            if provider in ('none', 'transfer'):
                continue
            res[provider] = {
                'mode': 'unique',
                'domain': [('type', '=', 'bank')],
            }
        return res
