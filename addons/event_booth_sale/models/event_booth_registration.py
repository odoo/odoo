# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventBoothRegistration(models.Model):
    _inherit = 'event.booth.registration'

    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', readonly=True, ondelete='cascade')
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Sales Order Line', readonly=True, ondelete='cascade')
    partner_id = fields.Many2one(
        compute='_compute_partner_id', readonly=False, store=True)
    state = fields.Selection(selection_add=[('paid', 'Paid')])

    @api.depends('sale_order_id')
    def _compute_partner_id(self):
        for registration in self:
            if registration.sale_order_id:
                registration.partner_id = registration.sale_order_id.partner_id

    def action_set_paid(self):
        self.ensure_one()
        self.booth_slot_ids.action_confirm(self)
        self.write({'state': 'paid'})
