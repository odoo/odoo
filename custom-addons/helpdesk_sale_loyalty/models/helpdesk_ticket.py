# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    coupons_count = fields.Integer('Coupons count', compute='_compute_coupons_count')
    coupon_ids = fields.Many2many('loyalty.card', string='Generated Coupons', copy=False)

    @api.depends('coupon_ids')
    def _compute_coupons_count(self):
        for ticket in self:
            ticket.coupons_count = len(ticket.coupon_ids)

    def open_coupons(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Coupons'),
            'res_model': 'loyalty.card',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.coupon_ids.ids)],
            'context': dict(self._context, create=False, edit=False, default_company_id=self.company_id.id),
        }
        if self.coupons_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.coupon_ids.id
            })
        return action
