# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    payment_provider_ids = fields.One2many(
        comodel_name='payment.provider',
        inverse_name='account_payment_method_id',
        store=True,
    )

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        for code, _desc in self.env['payment.provider']._fields['code'].selection:
            if code in ('none', 'custom'):
                continue
            res[code] = {'type': ('bank',)}
        return res

    def _get_available(self, payment_type=None, country=None, currency=None, current_journal=None):
        methods = super()._get_available(payment_type, country, currency, current_journal)
        return methods.filtered(
            lambda m: ('enabled', self.env.company) in m.payment_provider_ids.mapped(lambda p: (p.state, p.company_id))
        ) | methods.filtered(
            lambda m: ('test', self.env.company) in m.payment_provider_ids.mapped(lambda p: (p.state, p.company_id))
        ) | methods.filtered(lambda m: not m.payment_provider_ids)
