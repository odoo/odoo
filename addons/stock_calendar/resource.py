import datetime

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class resource_calendar_leaves(osv.osv):
    _inherit = "resource.calendar.leaves"
    _columns = {
        'group_id': fields.many2one('procurement.group', string="Procurement Group"),
    }

class resource_calendar(osv.osv):
    _inherit = "resource.calendar"

    #Could remove this as it does not help a lot
    def _calculate_next_day(self, cr, uid, ids, fields, names, context=None):
        res = {}
        for calend in self.browse(cr, uid, ids, context=context):
            # date1 = self.get_next_day(cr, uid, calend.id, datetime.utcnow() + relativedelta(days = 1))
            _format = '%Y-%m-%d %H:%M:%S'
            sched_date = self.schedule_days_get_date(
                cr, uid, calend.id, 1, day_date=datetime.datetime.utcnow(), compute_leaves=True)
            res[calend.id] = sched_date and sched_date.strftime(_format) or False
        return res

    _columns = {
            'next_day': fields.function(_calculate_next_day, string='Next day it should trigger', type='datetime'),
        }

    # Keep as it takes into account times
    def get_leave_intervals(self, cr, uid, id, resource_id=None,
                            start_datetime=None, end_datetime=None,
                            context=None):
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
        resource_calendar = self.browse(cr, uid, id, context=context)
        leaves = []
        for leave in resource_calendar.leave_ids:
            if leave.resource_id and not resource_id == leave.resource_id.id:
                continue
            date_from = datetime.datetime.strptime(leave.date_from, DEFAULT_SERVER_DATETIME_FORMAT)
            if end_datetime and date_from > end_datetime:
                continue
            date_to = datetime.datetime.strptime(leave.date_to, DEFAULT_SERVER_DATETIME_FORMAT)
            if start_datetime and date_to < start_datetime:
                continue
            leaves.append((date_from, date_to, leave.group_id.id))
        return leaves

    # --------------------------------------------------
    # Utility methods
    # --------------------------------------------------

    def interval_remove_leaves(self, cr, uid, interval, leave_intervals, context=None):
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
        if not interval:
            return interval
        if leave_intervals is None:
            leave_intervals = []
        intervals = []
        #leave_intervals = self.interval_clean(leave_intervals) NOT NECESSARY TO CLEAN HERE AS IT WOULD REMOVE GROUP INFO
        current_interval = list(interval)
        for leave in leave_intervals:
            if len(leave) > 2:
                current_group = False
                att_obj = self.pool.get("resource.calendar.attendance")
                if leave[2]:
                    if len(current_interval) > 2:
                        current_group = current_interval[2] and att_obj.browse(cr, uid, current_interval[2], context=context).group_id.id or False
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


class resource_calendar_attendance(osv.osv):
    _inherit = "resource.calendar.attendance"

    _columns = {
        'group_id': fields.many2one('procurement.group', 'Procurement Group'),
    }
