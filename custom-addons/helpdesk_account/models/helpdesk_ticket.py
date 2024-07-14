# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    invoices_count = fields.Integer('Credit Notes Count', compute='_compute_credit_notes_count')
    invoice_ids = fields.Many2many('account.move', string='Credit Notes', copy=False)

    @api.depends('invoice_ids')
    def _compute_credit_notes_count(self):
        for ticket in self:
            ticket.invoices_count = len(ticket.invoice_ids)

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Credit Notes'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': dict(self._context, default_partner_id=self.partner_id.id, default_move_type='out_refund', create=False)
        }
        if self.invoices_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.invoice_ids.id
            })
        return action
