# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime, time

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_line_ids = fields.One2many('purchase.order.line', 'partner_id', string="Purchase Lines")
    on_time_rate = fields.Float(
        "On-Time Delivery Rate", compute='_compute_on_time_rate',
        help="Over the past 12 months, number of products received on time / total number of ordered products.")

    @api.depends('purchase_line_ids')
    def _compute_on_time_rate(self):
        order_lines = self.env['purchase.order.line'].search([
            ('partner_id', 'in', self.ids),
            ('date_order', '>', fields.Date.today() - timedelta(365)),
            ('qty_received', '!=', 0),
        ]).filtered(lambda l: l.product_id.product_tmpl_id.type != 'service' and l.order_id.state in ['done', 'purchase'])
        partner_dict = {}
        for line in order_lines:
            on_time, ordered = partner_dict.get(line.partner_id, (0, 0))
            ordered += line.product_uom_qty
            on_time += sum(line.mapped('move_ids').filtered(lambda m: m.state == 'done' and m.date.date() <= m.purchase_line_id.date_planned.date()).mapped('quantity_done'))
            partner_dict[line.partner_id] = (on_time, ordered)
        seen_partner = self.env['res.partner']
        for partner, numbers in partner_dict.items():
            seen_partner |= partner
            on_time, ordered = numbers
            partner.on_time_rate = on_time / ordered * 100 if ordered else -1   # use negative number to indicate no data
        (self - seen_partner).on_time_rate = -1
