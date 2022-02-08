# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


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
        acquirers = self.env['payment.acquirer'].sudo().search([
            ('provider', 'in', self.mapped('code')),
            ('company_id', 'in', self.journal_id.company_id.ids),
        ])

        # Make sure to pick the active acquirer, if any.
        acquirers_map = dict()
        for acquirer in acquirers:
            current_value = acquirers_map.get((acquirer.provider, acquirer.company_id), False)
            if current_value and current_value.state != 'disabled':
                continue

            acquirers_map[(acquirer.provider, acquirer.company_id)] = acquirer

        for line in self:
            code = line.payment_method_id.code
            company = line.journal_id.company_id
            line.payment_acquirer_id = acquirers_map.get((code, company), False)

    def _get_payment_method_domain(self):
        # OVERRIDE
        domain = super()._get_payment_method_domain()
        information = self._get_payment_method_information().get(self.code)

        unique = information.get('mode') == 'unique'
        if unique:
            company_ids = self.env['payment.acquirer'].sudo().search([('provider', '=', self.code)]).mapped('company_id')
            if company_ids:
                domain = expression.AND([domain, [('company_id', 'in', company_ids.ids)]])

        return domain

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
