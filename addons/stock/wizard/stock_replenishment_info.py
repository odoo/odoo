# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from json import dumps
from datetime import datetime, time

from odoo import api, fields, models, SUPERUSER_ID
from odoo.osv.expression import AND
from odoo.tools import get_month, subtract, format_date


class StockReplenishmentInfo(models.TransientModel):
    _name = 'stock.replenishment.info'
    _description = 'Stock supplier replenishment information'
    _rec_name = 'orderpoint_id'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint')
    product_id = fields.Many2one('product.product', related='orderpoint_id.product_id')
    qty_to_order = fields.Float(related='orderpoint_id.qty_to_order')
    json_lead_days = fields.Char(compute='_compute_json_lead_days')
    json_replenishment_history = fields.Char(compute='_compute_json_replenishment_history')

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
        for replenishment_report in self:
            replenishment_history = []
            today = fields.Datetime.now()
            first_month = subtract(today, months=2)
            date_from, dummy = get_month(first_month)
            dummy, date_to = get_month(today)
            domain = [
                ('product_id', '=', replenishment_report.product_id.id),
                ('date', '>=', date_from),
                ('date', '<=', datetime.combine(date_to, time.max)),
                ('state', '=', 'done'),
                ('company_id', '=', replenishment_report.orderpoint_id.company_id.id)
            ]
            quantity_by_month_out = self.env['stock.move'].read_group(
                AND([domain, [('location_dest_id.usage', '=', 'customer')]]),
                ['date', 'product_qty'], ['date:month'])
            quantity_by_month_returned = self.env['stock.move'].read_group(
                AND([domain, [('location_id.usage', '=', 'customer')]]),
                ['date', 'product_qty'], ['date:month'])
            quantity_by_month_returned = {
                g['date:month']: g['product_qty'] for g in quantity_by_month_returned}
            for group in quantity_by_month_out:
                month = group['date:month']
                replenishment_history.append({
                    'name': month,
                    'quantity': group['product_qty'] - quantity_by_month_returned.get(month, 0),
                    'uom_name': replenishment_report.product_id.uom_id.display_name,
                })
            replenishment_report.json_replenishment_history = dumps({
                'template': 'stock.replenishmentHistory',
                'replenishment_history': replenishment_history
            })
