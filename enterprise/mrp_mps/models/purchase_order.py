# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    date_planned_mps = fields.Datetime(string='Scheduled Date', compute='_compute_date_planned_mps', store=True, index=True)

    @api.depends('order_line.date_planned', 'date_order')
    def _compute_date_planned_mps(self):
        for order in self:
            min_date = False
            for line in order.order_line:
                if not min_date or line.date_planned and line.date_planned < min_date:
                    min_date = line.date_planned
            # since we only care about the date, remove time part so that when search based on a date we can also match it
            if min_date:
                order.date_planned_mps = min_date.date()
            else:
                order.date_planned_mps = order.date_order.date()
