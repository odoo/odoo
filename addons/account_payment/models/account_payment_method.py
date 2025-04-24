# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    code = fields.Selection(
        selection_add=[('online_payment_provider', 'online_payment_provider')],
        ondelete={'online_payment_provider': 'cascade'},
    )

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['online_payment_provider'] = {
            'type': ('bank',),
        }
        return res

    @api.model
    def _get_available(self, payment_type=None, country=None, currency=None, current_journal=None):
        methods = super()._get_available(payment_type, country, currency, current_journal)
        return methods.filtered(lambda m: m.code != 'online_payment_provider')

    @api.model
    def _compute_available_payment_method_codes(self):
        super()._compute_available_payment_method_codes()
        for method in self:
            method.available_payment_method_codes = method.available_payment_method_codes.replace('online_payment_provider', '')
