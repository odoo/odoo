# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    next_delivery_date = fields.Datetime('Next Delivery Date', help="The date of the next delivery for this procurement group, when this group is on the purchase calendar of the orderpoint")
    next_purchase_date = fields.Datetime('Next Purchase Date', help="The date the next purchase order should be sent to the vendor")

    @api.multi
    def assign_group_date(self):
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        for procurement in self:
            orderpoint = Orderpoint.search([
                ('location_id', '=', procurement.location_id.id),
                ('product_id', '=', procurement.product_id.id)], limit=1)
            if orderpoint:
                date_planned = fields.Datetime.from_string(procurement.date_planned)
                purchase_date, delivery_date = orderpoint._get_previous_dates(date_planned)
                if purchase_date and delivery_date:
                    procurement.write({
                        'next_delivery_date': delivery_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'next_purchase_date': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    def _get_purchase_order_date(self, partner, schedule_date):
        if self.next_purchase_date:
            return fields.Datetime.from_string(self.next_purchase_date)
        return super(ProcurementOrder, self)._get_purchase_order_date(partner, schedule_date)

    def _get_purchase_schedule_date(self):
        if self.next_delivery_date:
            return datetime.strptime(self.next_delivery_date, DEFAULT_SERVER_DATETIME_FORMAT)
        return super(ProcurementOrder, self)._get_purchase_schedule_date()

    def _prepare_purchase_order_line(self, po, supplier):
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)
        if self.next_delivery_date:
            res.update({'date_planned': self.next_delivery_date})
        return res

    def _procurement_from_orderpoint_get_order(self):
        return 'location_id, purchase_calendar_id, calendar_id'

    def _procurement_from_orderpoint_get_grouping_key(self, orderpoint_ids):
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids[0])
        return (orderpoint.location_id.id, orderpoint.purchase_calendar_id.id, orderpoint.calendar_id.id)

    def _procurement_from_orderpoint_get_groups(self, orderpoint_ids):
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids[0])
        res_groups = []
        date_groups = orderpoint._get_group()
        for date, group in date_groups:
            if orderpoint.calendar_id and orderpoint.calendar_id.attendance_ids:
                date1, date2 = orderpoint._get_next_dates(date, group)
                res_groups += [{'to_date': date2, 'procurement_values': {'group': group, 'date': date1, 'purchase_date': date}}]  # date1/date2 as deliveries and date as purchase confirmation date
            else:
                res_groups += [{'to_date': False, 'procurement_values': {'group': group, 'date': date, 'purchase_date': date}}]
        return res_groups

    def _procurement_from_orderpoint_post_process(self, orderpoint_ids):
        self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids).write({
            'last_execution_date': datetime.utcnow().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return super(ProcurementOrder, self)._procurement_from_orderpoint_post_process(orderpoint_ids)
