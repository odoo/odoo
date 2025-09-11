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
    suggest_based_on = fields.Char(default='30_days')
    suggest_days = fields.Integer(default=7)
    suggest_percent = fields.Integer(default=100)
    group_rfq = fields.Selection(
        [('default', 'On Order'), ('day', 'Daily'), ('week', 'Weekly'), ('all', 'Always')],
        string='Group RFQ', required=True, default='default', help="Define if RFQ should be grouped \
        together based on expected arrival.\n \
        On Order: Replenishment needs will be grouped together except for MTO.\n \
        Daily: Replenishment needs will be grouped if the expected arrival is the same day\n \
        Weekly: Replenishment needs will be grouped if the expected arrival is the same week or week day\n \
        Always: Replenishment needs will always be grouped.")
    group_on = fields.Selection([
        ('default', 'Expected Date'),
        ('1', 'Monday'),
        ('2', 'Tuesday'),
        ('3', 'Wednesday'),
        ('4', 'Thursday'),
        ('5', 'Friday'),
        ('6', 'Saturday'),
        ('7', 'Sunday'),
    ], string='Week Day', required=True, default='default')

    @api.depends('purchase_line_ids')
    def _compute_on_time_rate(self):
        date_order_days_delta = int(self.env['ir.config_parameter'].sudo().get_param('purchase_stock.on_time_delivery_days', default='365'))
        order_lines = self.env['purchase.order.line'].search([
            ('partner_id', 'in', self.ids),
            ('date_order', '>', fields.Date.today() - timedelta(date_order_days_delta)),
            ('qty_received', '!=', 0),
            ('order_id.state', '=', 'purchase'),
            ('product_id', 'in', self.env['product.product'].sudo()._search([('type', '!=', 'service')]))
        ])
        lines_quantity = defaultdict(lambda: 0)
        moves = self.env['stock.move'].search([
            ('purchase_line_id', 'in', order_lines.ids),
            ('state', '=', 'done')])
        # Fetch fields from db and put them in cache.
        order_lines.read(['date_planned', 'partner_id', 'product_uom_qty'], load='')
        moves.read(['purchase_line_id', 'date'], load='')
        moves = moves.filtered(lambda m: m.date.date() <= m.purchase_line_id.date_planned.date())
        for move, quantity in zip(moves, moves.mapped('quantity')):
            lines_quantity[move.purchase_line_id.id] += quantity
        partner_dict = {}
        for line in order_lines:
            on_time, ordered = partner_dict.get(line.partner_id, (0, 0))
            ordered += line.product_uom_qty
            on_time += lines_quantity[line.id]
            partner_dict[line.partner_id] = (on_time, ordered)
        seen_partner = self.env['res.partner']
        for partner, numbers in partner_dict.items():
            seen_partner |= partner
            on_time, ordered = numbers
            partner.on_time_rate = on_time / ordered * 100 if ordered else -1   # use negative number to indicate no data
        (self - seen_partner).on_time_rate = -1
