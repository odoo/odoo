# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    calendar_id = fields.Many2one('resource.calendar', string='Calendar',
                                       help="In the calendar you can define the days that the goods will be delivered.  That way the scheduler will only take into account the goods needed until the second delivery and put the procurement date as the first delivery.")
    purchase_calendar_id = fields.Many2one('resource.calendar', string='Purchase Calendar')
    last_execution_date = fields.Datetime(string='Last Execution Date', readonly=True)

    @api.multi
    def _prepare_procurement_values(self, product_qty, date=False, purchase_date=False, group=False):
        res = super(StockWarehouseOrderpoint, self)._prepare_procurement_values(product_qty, date=date, group=group)
        res.update({
            'next_delivery_date': date,
            'next_purchase_date': purchase_date})
        return res
