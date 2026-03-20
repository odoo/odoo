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
        together based on expected arrival, except for dropship operations.\n \
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
        date_order_days_delta = self.env['ir.config_parameter'].sudo().get_int('purchase_stock.on_time_delivery_days') or 365
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
        order_lines.read(['date_promised', 'partner_id', 'product_uom_qty'], load='')
        moves.read(['purchase_line_id', 'date'], load='')
        moves = moves.filtered(lambda m: m.date.date() <= m.purchase_line_id.date_promised.date())
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
        """ Returns product vendors first if highlight_supplier flag in context"""
        res = super().name_search(name, domain, operator, limit)
        if not self.env.context.get('highlight_supplier') or not self.env.context.get('product_id'):  # Flag for replenish wizard
            return res

        product = self.env['product.product'].browse(self.env.context['product_id'])
        listed_vendors_ids = {partner_id for partner_id, _ in res}

        missing_vendors_ids = list(set(product.seller_ids.partner_id.ids) - listed_vendors_ids)
        if missing_vendors_ids:  # Vendors not in res due to limit (eg. res: Abigail...Wood and Zut is a vendor)
            vendor_domain = [('id', 'in', missing_vendors_ids)]
            res.extend(super().name_search(name, vendor_domain, operator, limit))

        res.sort(key=lambda partner: 0 if partner[0] in product.seller_ids.partner_id.ids else 1)
        return res[:limit] if limit else res

    @api.depends('name')
    @api.depends_context('highlight_supplier')
    def _compute_display_name(self):
        """ Displays partner in bold if highlight_supplier flag in context"""
        super()._compute_display_name()
        ctx = self.env.context
        if not ctx.get("highlight_supplier") or not ctx.get("formatted_display_name") or not ctx.get("product_id"):
            return  # If highlight flag OFF or dropdown not expanded return without styling

        product = self.env['product.product'].browse(ctx['product_id'])
        for rec in self:
            if rec.id in product.seller_ids.partner_id.ids:
                rec.display_name = f"**{rec.display_name}**"  # Bold
