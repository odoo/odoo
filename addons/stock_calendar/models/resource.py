# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    group_id = fields.Many2one('procurement.group', 'Procurement Group')


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    group_id = fields.Many2one('procurement.group', string="Procurement Group")


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    # Keep as it takes into account times
    @api.multi
    def _get_leave_intervals(self, resource_id=None,
                             start_datetime=None, end_datetime=None):
        """Get the leaves of the calendar. Leaves can be filtered on the resource,
        the start datetime or the end datetime.

        :param int resource_id: the id of the resource to take into account when
                                computing the leaves. If not set, only general
                                leaves are computed. If set, generic and
                                specific leaves are computed.
        :param datetime start_datetime: if provided, do not take into account leaves
                                        ending before this date.
        :param datetime end_datetime: if provided, do not take into account leaves
                                        beginning after this date.

        :return list leaves: list of tuples (start_datetime, end_datetime) of
                             leave intervals
        """
        # TDE FIXME: waw, overriding completely a method + changing its result
        # and its behavior, very nice. Please FIXME.
        self.ensure_one()
        leaves = []
        for leave in self.leave_ids:
            if leave.resource_id and not resource_id == leave.resource_id.id:
                continue
            date_from = fields.Datetime.from_string(leave.date_from)
            if end_datetime and date_from > end_datetime:
                continue
            date_to = fields.Datetime.from_string(leave.date_to)
            if start_datetime and date_to < start_datetime:
                continue
            leaves.append((date_from, date_to, leave.group_id.id))
        return leaves

    # --------------------------------------------------
    # Utility methods
    # --------------------------------------------------

    @api.model
    def _interval_remove_leaves(self, interval, leave_intervals):
        """ Utility method that remove leave intervals from a base interval:

         - clean the leave intervals, to have an ordered list of not-overlapping
           intervals
         - initiate the current interval to be the base interval
         - for each leave interval:

          - finishing before the current interval: skip, go to next
          - beginning after the current interval: skip and get out of the loop
            because we are outside range (leaves are ordered)
          - beginning within the current interval: close the current interval
            and begin a new current interval that begins at the end of the leave
            interval
          - ending within the current interval: update the current interval begin
            to match the leave interval ending
          - take into account the procurement group when needed

        :param tuple interval: a tuple (beginning datetime, ending datetime) that
                               is the base interval from which the leave intervals
                               will be removed
        :param list leave_intervals: a list of tuples (beginning datetime, ending datetime)
                                    that are intervals to remove from the base interval
        :return list intervals: a list of tuples (begin datetime, end datetime)
                                that are the remaining valid intervals """
        # TDE FIXME: waw, overriding completely a method + changing its result
        # and its behavior, very nice. Please FIXME.
        if not interval:
            return interval
        if leave_intervals is None:
            leave_intervals = []
        intervals = []
        #leave_intervals = self._interval_merge(leave_intervals) NOT NECESSARY TO CLEAN HERE AS IT WOULD REMOVE GROUP INFO
        current_interval = list(interval)
        for leave in leave_intervals:
            if len(leave) > 2:
                current_group = False
                Att = self.env["resource.calendar.attendance"]
                if leave[2]:
                    if len(current_interval) > 2:
                        current_group = current_interval[2] and Att.browse(current_interval[2]).group_id.id or False
                    if leave[2] != current_group:
                        continue
            if leave[1] <= current_interval[0]:
                continue
            if leave[0] >= current_interval[1]:
                break

            if current_interval[0] < leave[0] < current_interval[1]:
                current_interval[1] = leave[0]
                intervals.append((current_interval[0], current_interval[1]))
                current_interval = [leave[1], interval[1]]
            # if current_interval[0] <= leave[1] <= current_interval[1]:
            if current_interval[0] <= leave[1]:
                current_interval[0] = leave[1]
        if current_interval and current_interval[0] < interval[1]:  # remove intervals moved outside base interval due to leaves
            if len(interval) > 2:
                intervals.append((current_interval[0], current_interval[1], interval[2]))
            else:
                intervals.append((current_interval[0], current_interval[1],))
        return intervals
