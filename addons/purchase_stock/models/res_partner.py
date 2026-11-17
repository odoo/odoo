# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime, time
from collections import defaultdict

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_line_ids = fields.One2many('purchase.order.line', 'partner_id', string="Purchase Lines")
    on_time_rate = fields.Float(
        "On-Time Delivery Rate", compute='_compute_on_time_rate',
        help="Over the past x days; the number of products received on time divided by the number of ordered products."\
            "x is either the System Parameter purchase_stock.on_time_delivery_days or the default 365")

    @api.depends('purchase_line_ids')
    def _compute_on_time_rate(self):
        date_order_days_delta = int(self.env['ir.config_parameter'].sudo().get_param('purchase_stock.on_time_delivery_days', default='365'))
        # prefetching for future filtering and calculation logic
        order_lines = self.env['purchase.order.line'].search_fetch(
            domain=[
                ('partner_id', 'in', self.ids),
                ('date_order', '>', fields.Date.today() - timedelta(date_order_days_delta)),
                ('move_ids', 'any', [
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '!=', 'supplier'),
                    ('origin_returned_move_id', '=', False),
                ]),
                ('order_id.state', 'in', ['done', 'purchase']),
                ('product_id', 'in', self.env['product.product'].sudo()._search([('type', '!=', 'service')])),
            ],
            field_names=['date_planned', 'partner_id', 'product_uom_qty'],
        )
        lines_quantity = defaultdict(lambda: 0)
        # Caveat: If you're going to edit the following lines, make sure the business logic in the vendor delay report
        # matches it and produces identical results. (eg filtering, UoM conversions, rounding logic)
        moves = self.env['stock.move'].search_fetch(
            domain=[
                ('purchase_line_id', 'in', order_lines.ids),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '!=', 'supplier'),
                ('origin_returned_move_id', '=', False),
            ],
            # `product_id` is needed because kits' component moves all have that kit's POL.
            field_names=['purchase_line_id', 'date', 'quantity', 'product_uom', 'product_id'],
        )
        moves = moves.filtered(lambda m: m.date.date() <= m.purchase_line_id.date_planned.date())
        for move in moves:
            lines_quantity[move.purchase_line_id.id] += move.product_uom._compute_quantity(
                move.quantity, move.product_id.uom_id, round=False)
        partner_dict = {}
        for line in order_lines:
            on_time, ordered = partner_dict.get(line.partner_id, (0, 0))
            ordered += line.product_uom_qty
            on_time += min(lines_quantity[line.id], line.product_uom_qty)
            partner_dict[line.partner_id] = (on_time, ordered)
        seen_partner = self.env['res.partner']
        for partner, numbers in partner_dict.items():
            seen_partner |= partner
            on_time, ordered = numbers
            partner.on_time_rate = on_time / ordered * 100 if ordered else -1   # use negative number to indicate no data
        (self - seen_partner).on_time_rate = -1
