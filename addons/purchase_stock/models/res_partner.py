# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime, time
from collections import defaultdict

from odoo import api, fields, models
from odoo.osv import expression


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

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        res = super().name_search(name, domain, operator, limit)
        if not self.env.context.get('highlight_supplier', False):  # Flag for replenish wizard
            return res

        product = self.env['product.product'].browse(self.env.context['product_id'])
        seen_ids = {pid for pid, _ in res}
        missing_ids = list(set(product.seller_ids.partner_id.ids) - seen_ids)
        if missing_ids:  # Vendors not in res due to limit
            vendor_domain = expression.AND([domain or [], [('id', 'in', missing_ids)]])
            res.extend(super().name_search(name, vendor_domain, operator, limit))

        res.sort(key=lambda partner: 0 if partner[0] in product.seller_ids.partner_id.ids else 1)
        return res[:limit] if limit else res

    @api.depends('name')
    def _compute_display_name(self):
        super()._compute_display_name()
        ctx = self.env.context
        if not (ctx.get('product_id', 0) and ctx.get("formatted_display_name", 0) and ctx.get("highlight_supplier", 0)):
            return
        product = self.env['product.product'].browse(ctx['product_id'])
        for rec in self:
            if rec.id in product.seller_ids.partner_id.ids:
                rec.display_name = f"**{rec.display_name}**"
