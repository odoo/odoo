# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    next_delivery_date = fields.Datetime(string='Next Delivery Date', help="The date of the next delivery for this procurement group, when this group is on the purchase calendar of the orderpoint")
    next_purchase_date = fields.Datetime(string='Next Purchase Date', help="The date the next purchase order should be sent to the vendor")

    @api.multi
    def assign_group_date(self):
        StockWarehouseOrderpoint = self.env['stock.warehouse.orderpoint']
        for procurement in self:
            order_points = StockWarehouseOrderpoint.search([('location_id', '=', procurement.location_id.id), ('product_id', '=', procurement.product_id.id)], limit=1)
            if order_points:
                date_planned = fields.Datetime.from_string(procurement.date_planned)
                purchase_date, delivery_date = self._get_previous_dates(order_points, date_planned)
                if purchase_date and delivery_date:
                    self.write({'next_delivery_date': fields.Datetime.to_string(delivery_date), 'next_purchase_date': fields.Datetime.to_string(purchase_date)})

    @api.v8
    def _get_purchase_order_date(self, schedule_date):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :param datetime schedule_date: desired Scheduled Date for the Purchase Order lines.
           :rtype: datetime
           :return: the desired Order Date for the PO
        """
        self.ensure_one()
        if self.next_purchase_date:
            return fields.Datetime.from_string(self.next_purchase_date)
        return super(ProcurementOrder, self)._get_purchase_order_date(schedule_date)

    @api.v7
    def _get_purchase_order_date(self, cr, uid, procurement, company, schedule_date, context=None):
        return self.browse(cr, uid, procurement, company, schedule_date, context)._get_purchase_order_date()

    @api.v8
    def _get_purchase_schedule_date(self):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement.

           :param browse_record procurement: the procurement for which a PO will be created.
           :rtype: datetime
           :return: the desired Schedule Date for the PO lines
        """
        self.ensure_one()
        if self.next_delivery_date:
            return fields.Datetime.from_string(self.next_delivery_date)
        return super(ProcurementOrder, self)._get_purchase_schedule_date()

    @api.v7
    def _get_purchase_schedule_date(self, cr, uid, procurement, context=None):
        return self.browse(cr, uid, procurement, context)._get_purchase_schedule_date()

    def _prepare_purchase_order_line(self, po, supplier):
        self.ensure_one()
        res = super(ProcurementOrder, self)._prepare_purchase_order_line(po, supplier)
        if self.next_delivery_date:
            res['date_planned'] = self.next_delivery_date
        return res

    def _get_previous_dates(self, orderpoint, start_date=False):
        """
        Date should be given in utc
        """
        ResourceCalendarAttendance = self.env['resource.calendar.attendance'].with_context(no_round_hours=True)
        # Date should be converted to the correct timezone
        # First check if the orderpoint has a Calendar as it should be delivered at this calendar date
        purchase_date = False
        delivery_date = start_date
        if orderpoint.calendar_id and orderpoint.calendar_id.attendance_ids:
            [res] = orderpoint.calendar_id.with_context(no_round_hours=True)._schedule_days(-1, start_date, compute_leaves=True)
            if res and res[0][0] < start_date:
                group_to_find = res[0][2] and ResourceCalendarAttendance.browse(res[0][2]).group_id.id or False
                delivery_date = res[0][0]
                found_date = delivery_date
                if orderpoint.purchase_calendar_id and orderpoint.purchase_calendar_id.attendance_ids:
                    while not purchase_date:
                        found_date = found_date + relativedelta(days=-1)  # won't allow to deliver within the day
                        [res] = orderpoint.purchase_calendar_id.with_context(no_round_hours=True)._schedule_days(-1, found_date, compute_leaves=True)
                        for re in res:
                            group = re[2] and ResourceCalendarAttendance.browse(re[2]).group_id.id or False
                            if not purchase_date and (group_to_find and group_to_find == group or (not group_to_find)):
                                purchase_date = re[0]
        else:
            delivery_date = start_date or datetime.utcnow()
        return purchase_date, delivery_date

    def _get_next_dates(self, orderpoint, new_date=False, group=False):
        ResourceCalendarAttendance = self.env['resource.calendar.attendance'].with_context(no_round_hours=True)
        if not new_date:
            new_date = datetime.utcnow()
        now_date = datetime.utcnow()
        # Search first calendar day (without group)
        [res] = orderpoint.calendar_id.with_context(no_round_hours=True)._schedule_days(1, new_date, compute_leaves=True)
        att_group = res and res[0][2] and ResourceCalendarAttendance.browse(res[0][2]).group_id.id or False
        #If hours are smaller than the current date, search a day further
        if res and res[0][0] < now_date:
            new_date = res[0][1] + relativedelta(days=1)
            [res] = orderpoint.calendar_id.with_context(no_round_hours=True)._schedule_days(1, new_date, compute_leaves=True)
            for re in res:
                att_group = False
                if re[2]:
                    att_group = ResourceCalendarAttendance.browse(re[2]).group_id.id
                    if att_group == group:
                        break

        # If you can find an entry and you have a group to match, but it does not, search further until you find one that corresponds
        number = 0
        while res and group and att_group != group and number < 100:
            number += 1
            new_date = res[0][1] + relativedelta(days=1)
            [res] = orderpoint.calendar_id.with_context(no_round_hours=True)._schedule_days(1, new_date, compute_leaves=True)
            att_group = False
            for re in res:
                if re[2]:
                    att_group = ResourceCalendarAttendance.browse(re[2]).group_id.id
                    if att_group == group:
                        break
        #number as safety pall for endless loops
        if number >= 100:
            res = False

        # If you found a solution(first date), you need the second date until the next delivery because you need to deliver
        # everything needed until the second date on the first date
        if res:
            date1 = res[0][1]
            new_date = res[0][1] + relativedelta(days=1)
            [res] = orderpoint.calendar_id.with_context(no_round_hours=True)._schedule_days(1, new_date, compute_leaves=True)
            if res:
                return (date1, res[0][1])
        return (False, False)

    def _get_group(self, orderpoint):
        """
            Will return the groups and the end dates of the intervals of the purchase calendar
            that need to be executed now.
            If a purchase calendar is defined, it should give the
            :return [(date, group)]
        """
        #Check if orderpoint has last execution date and calculate if we need to calculate again already
        ResourceCalendarAttendance = self.env['resource.calendar.attendance']
        group = False
        date = False
        now_date = datetime.utcnow()
        res_intervals = []
        if orderpoint.purchase_calendar_id and orderpoint.purchase_calendar_id.attendance_ids:
            if orderpoint.last_execution_date:
                new_date = fields.Datetime.from_string(orderpoint.last_execution_date)
            else:
                new_date = datetime.utcnow()
            # TDE note: I bet accessing interval[2] will crash, no ? this code seems very louche
            [intervals] = orderpoint.purchase_calendar_id.with_context(no_round_hours=True)._schedule_days(1, new_date, compute_leaves=True)
            for interval in intervals:
                # If last execution date, interval should start after it in order not to execute the same orderpoint twice
                # TODO: Make the interval a little bigger
                if (orderpoint.last_execution_date and (interval[0] > new_date and interval[0] < now_date)) or (not orderpoint.last_execution_date and interval[0] < now_date and interval[1] > now_date):
                    group = ResourceCalendarAttendance.with_context(no_round_hours=True).browse(interval[2]).group_id.id
                    date = interval[1]
                    res_intervals += [(date, group), ]
        else:
            return [(now_date, None)]
        return res_intervals

    @api.model
    def _procurement_from_orderpoint_get_order(self):
        return 'location_id, purchase_calendar_id, calendar_id'

    @api.model
    def _procurement_from_orderpoint_get_grouping_key(self, orderpoint_ids):
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids)
        return (orderpoint.location_id.id, orderpoint.purchase_calendar_id.id, orderpoint.calendar_id.id)

    @api.model
    def _procurement_from_orderpoint_get_groups(self, orderpoint_ids):
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids)
        res_groups = []
        date_groups = self._get_group(orderpoint)
        for date, group in date_groups:
            if orderpoint.calendar_id and orderpoint.calendar_id.attendance_ids:
                date1, date2 = self._get_next_dates(orderpoint, date, group)
                res_groups += [{'to_date': date2, 'procurement_values': {'group': group, 'date': date1, 'purchase_date': date}}]  # date1/date2 as deliveries and date as purchase confirmation date
            else:
                res_groups += [{'to_date': False, 'procurement_values': {'group': group, 'date': date, 'purchase_date': date}}]
        return res_groups

    @api.model
    def _procurement_from_orderpoint_post_process(self, orderpoint_ids):
        orderpoint_ids = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids)
        orderpoint_ids.write({'last_execution_date': fields.Datetime.to_string(datetime.utcnow())})
        return super(ProcurementOrder, self)._procurement_from_orderpoint_post_process(orderpoint_ids)
