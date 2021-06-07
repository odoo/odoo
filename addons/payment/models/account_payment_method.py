# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    payment_acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        compute='_compute_payment_acquirer_id',
        search='_search_payment_acquirer_id'
    )
    payment_acquirer_state = fields.Selection(
        related='payment_acquirer_id.state'
    )

    @api.depends('payment_method_id')
    def _compute_payment_acquirer_id(self):
        for line in self:
            code = line.payment_method_id.code
            line.payment_acquirer_id = self.env['payment.acquirer'].search([
                ('provider', '=', code), ('company_id', '=', line.journal_id.company_id.id)
            ], limit=1)

    def _search_payment_acquirer_id(self, operator, operand):
        return [('id', operator, operand)]

    def action_open_acquirer_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Acquirer'),
            'view_mode': 'form',
            'res_model': 'payment.acquirer',
            'target': 'current',
            'res_id': self.payment_acquirer_id.id
        }
