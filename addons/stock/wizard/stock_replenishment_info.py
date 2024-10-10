# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from json import dumps
from datetime import datetime, time

from odoo import api, fields, models, SUPERUSER_ID
from odoo.osv.expression import AND
from odoo.tools import get_month, subtract, format_date, get_fiscal_year


class StockReplenishmentInfo(models.TransientModel):
    _name = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'
    _rec_name = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint')
    product_id = fields.Many2one('product.product', related='orderpoint_id.product_id')
    qty_to_order = fields.Float(related='orderpoint_id.qty_to_order')
    json_lead_days = fields.Char(compute='_compute_json_lead_days')
    json_replenishment_history = fields.Char(compute='_compute_json_replenishment_history')
    periods = fields.Selection([
        ('year', 'Yearly'),
        ('month', 'Monthly'),
    ], string='Stock replenishment info period',
        default='year',
        help="The stock replenishments infos can be either ordered monthly or yearly.")

    @api.depends('orderpoint_id')
    def _compute_json_lead_days(self):
        self.json_lead_days = False
        for replenishment_report in self:
            if not replenishment_report.orderpoint_id.product_id or not replenishment_report.orderpoint_id.location_id:
                continue
            orderpoint = replenishment_report.orderpoint_id
            orderpoints_values = orderpoint._get_lead_days_values()
            dummy, lead_days_description = orderpoint.rule_ids._get_lead_days(
                orderpoint.product_id, **orderpoints_values)
            replenishment_report.json_lead_days = dumps({
                'template': 'stock.leadDaysPopOver',
                'lead_days_date': format_date(self.env, replenishment_report.orderpoint_id.lead_days_date),
                'lead_days_description': lead_days_description,
                'today': format_date(self.env, fields.Date.today()),
                'trigger': orderpoint.trigger,
                'qty_forecast': self.env['ir.qweb.field.float'].value_to_html(orderpoint.qty_forecast, {'decimal_precision': 'Product Unit of Measure'}),
                'qty_to_order': self.env['ir.qweb.field.float'].value_to_html(orderpoint.qty_to_order, {'decimal_precision': 'Product Unit of Measure'}),
                'product_min_qty': self.env['ir.qweb.field.float'].value_to_html(orderpoint.product_min_qty, {'decimal_precision': 'Product Unit of Measure'}),
                'product_max_qty': self.env['ir.qweb.field.float'].value_to_html(orderpoint.product_max_qty, {'decimal_precision': 'Product Unit of Measure'}),
                'product_uom_name': orderpoint.product_uom_name,
                'virtual': orderpoint.trigger == 'manual' and orderpoint.create_uid.id == SUPERUSER_ID,
            })

    @api.depends('orderpoint_id')
    def _compute_json_replenishment_history(self):
        period_setting = self.orderpoint_id.company_id.stock_replenishment_info_periods
        today = fields.Datetime.now()
        get_period = get_fiscal_year if period_setting == 'year' else get_month
        group_period = "date:year" if period_setting == 'year' else "date:month"
        start_period = subtract(today, year=2) if period_setting == 'year' else subtract(today, months=2)
        for replenishment_report in self:
            replenishment_history = []
            date_from, dummy = get_period(start_period)
            dummy, date_to = get_period(today)
            domain = [
                ('product_id', '=', replenishment_report.product_id.id),
                ('date', '>=', date_from),
                ('date', '<=', datetime.combine(date_to, time.max)),
                ('state', '=', 'done'),
                ('company_id', '=', replenishment_report.orderpoint_id.company_id.id)
            ]
            quantity_by_period_out = self.env['stock.move'].read_group(
                AND([domain, [('location_dest_id.usage', '=', 'customer')]]),
                ['date', 'product_qty'], [group_period])
            quantity_by_period_returned = self.env['stock.move'].read_group(
                AND([domain, [('location_id.usage', '=', 'customer')]]),
                ['date', 'product_qty'], [group_period])
            quantity_by_period_returned = {
                g[group_period]: g['product_qty'] for g in quantity_by_period_returned}
            for group in quantity_by_period_out:
                period = group[group_period]
                replenishment_history.append({
                    'name': period,
                    'quantity': group['product_qty'] - quantity_by_period_returned.get(period, 0),
                    'uom_name': replenishment_report.product_id.uom_id.display_name,
                })
            replenishment_report.json_replenishment_history = dumps({
                'template': 'stock.replenishmentHistory',
                'replenishment_history': replenishment_history
            })