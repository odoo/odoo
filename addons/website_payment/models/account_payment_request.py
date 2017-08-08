# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountPaymentRequest(models.Model):
    _inherit = "account.payment.request"

    @api.multi
    def _prepare_payment_acquirer(self, values=None):
        self.ensure_one()
        result = super(AccountPaymentRequest, self)._prepare_payment_acquirer(values)
        if result:
            result['tokens'] = self.env['payment.token'].search([
                ('partner_id', '=', self.partner_id.id),
                ('acquirer_id', 'in', [payment.id for payment in result['acquirers']])
            ])
            result['save_option'] = True
        return result
