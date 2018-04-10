# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    calendar_id = fields.Many2one(
        'resource.calendar', 'Calendar',
        help="In the calendar you can define the days that the goods will be delivered. That way the scheduler will "
             "only take into account the goods needed until the second delivery and put the procurement date as the first delivery.")
    purchase_calendar_id = fields.Many2one('resource.calendar', 'Purchase Calendar')
    last_execution_date = fields.Datetime('Last Execution Date', readonly=True)

    def _prepare_procurement_values(self, product_qty, date=False, purchase_date=False, group=False):
        res = super(StockWarehouseOrderpoint, self)._prepare_procurement_values(product_qty, date=date, group=group)
        res.update({
            'next_delivery_date': date,
            'next_purchase_date': purchase_date})
        return res

    def _get_group(self):
        """
            Will return the groups and the end dates of the intervals of the purchase calendar
            that need to be executed now.
            If a purchase calendar is defined, it should give the
            :return [(date, group)]
        """
        # TDE FIXME: unused context key 'no_round_hours' removed
        # Check if orderpoint has last execution date and calculate if we need to calculate again already
        Attendance = self.env["resource.calendar.attendance"]
        group = False
        date = False
        now_date = datetime.utcnow()
        res_intervals = []
        if self.purchase_calendar_id and self.purchase_calendar_id.attendance_ids:
            if self.last_execution_date:
                new_date = datetime.strptime(self.last_execution_date, DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                new_date = datetime.utcnow()
            # TDE note: I bet accessing interval[2] will crash, no ? this code seems very louche
            intervals = self.purchase_calendar_id._schedule_days(1, new_date, compute_leaves=True)
            for interval in intervals:
                # If last execution date, interval should start after it in order not to execute the same orderpoint twice
                # TODO: Make the interval a little bigger
                if (self.last_execution_date and (interval[0] > new_date and interval[0] < now_date)) or (not self.last_execution_date and interval[0] < now_date and interval[1] > now_date):
                    group = Attendance.browse(interval[2]).group_id.id
                    date = interval[1]
                    res_intervals += [(date, group), ]
        else:
            return [(False, None)]
        return res_intervals

    def _get_previous_dates(self, start_date=False):
        """
        Date should be given in utc
        """
        # TDE FIXME: unused context key 'no_round_hours' removed
        Attendance = self.env["resource.calendar.attendance"]
        # First check if the orderpoint has a Calendar as it should be delivered at this calendar date
        purchase_date = False
        delivery_date = start_date
        if self.calendar_id and self.calendar_id.attendance_ids:
            res = self.calendar_id._schedule_days(-1, start_date, compute_leaves=True)
            if res and res[0][0] < start_date:
                group_to_find = res[0][2] and Attendance.browse(res[0][2]).group_id.id
                delivery_date = res[0][0]
                found_date = delivery_date
                if self.purchase_calendar_id and self.purchase_calendar_id.attendance_ids:
                    while not purchase_date:
                        found_date = found_date + relativedelta(days=-1)  # won't allow to deliver within the day
                        res = self.purchase_calendar_id._schedule_days(-1, found_date, compute_leaves=True)
                        for re in res:
                            group = re[2] and Attendance.browse(re[2]).group_id.id
                            found_date = re[0]
                            if not purchase_date and (group_to_find and group_to_find == group or (not group_to_find)):
                                purchase_date = re[0]
        else:
            delivery_date = start_date or datetime.utcnow()
        return purchase_date, delivery_date

    def _get_next_dates(self, new_date=False, group=False):
        # TDE FIXME: unused context key 'no_round_hours' removed
        Attendance = self.env["resource.calendar.attendance"]
        if not new_date:
            new_date = datetime.utcnow()
        now_date = datetime.utcnow()

        # Search first calendar day (without group)
        res = self.calendar_id._schedule_days(1, new_date, compute_leaves=True)
        att_group = res and res[0][2] and Attendance.browse(res[0][2]).group_id.id
        # If hours are smaller than the current date, search a day further
        if res and res[0][0] < now_date:
            new_date = res[0][1] + relativedelta(days=1)
            res = self.calendar_id._schedule_days(1, new_date, compute_leaves=True)
            for re in res:
                att_group = False
                if re[2]:
                    att_group = Attendance.browse(re[2]).group_id.id
                    if att_group == group:
                        break

        # If you can find an entry and you have a group to match, but it does not, search further until you find one that corresponds
        number = 0
        while res and group and att_group != group and number < 100:
            number += 1
            new_date = res[0][1] + relativedelta(days=1)
            res = self.calendar_id._schedule_days(1, new_date, compute_leaves=True)
            att_group = False
            for re in res:
                if re[2]:
                    att_group = Attendance.browse(re[2]).group_id.id
                    if att_group == group:
                        break
        # number as safety pall for endless loops
        if number >= 100:
            res = False

        # If you found a solution(first date), you need the second date until the next delivery because you need to deliver
        # everything needed until the second date on the first date
        if res:
            date1 = res[0][1]
            new_date = res[0][1] + relativedelta(days=1)
            res = self.calendar_id._schedule_days(1, new_date, compute_leaves=True)
            if res:
                return (date1, res[0][1])
        return (False, False)
