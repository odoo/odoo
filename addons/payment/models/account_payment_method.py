# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    payment_acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        compute='_compute_payment_acquirer_id',
        store=True
    )
    payment_acquirer_state = fields.Selection(
        related='payment_acquirer_id.state'
    )

    @api.depends('payment_method_id')
    def _compute_payment_acquirer_id(self):
        acquirers = self.env['payment.acquirer'].search([
            ('provider', 'in', self.mapped('code')),
            ('company_id', 'in', self.journal_id.company_id.ids),
        ])
        acquirers_map = {(x.provider, x.company_id): x for x in acquirers}
        for line in self:
            code = line.payment_method_id.code
            company = line.journal_id.company_id
            line.payment_acquirer_id = acquirers_map.get((code, company), False)

    def action_open_acquirer_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Acquirer'),
            'view_mode': 'form',
            'res_model': 'payment.acquirer',
            'target': 'current',
            'res_id': self.payment_acquirer_id.id
        }
