# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

from collections import defaultdict
from datetime import timedelta
from itertools import groupby
from pytz import timezone, utc

from odoo import api, models, _
from odoo.tools.misc import get_lang
from odoo.tools import format_time


def convert_time_to_string(env, time, time_format='medium'):
    lang_time_string = time.strftime(get_lang(env).time_format)
    lang_time = time.strptime(lang_time_string, get_lang(env).time_format)
    return format_time(env, lang_time, tz=timezone(env.user.tz or 'UTC'), time_format=time_format)


def format_date(env, date):
    return date.strftime(get_lang(env).date_format)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.model
    def _get_leave_interval(self, date_from, date_to, employee_ids):
        # Validated hr.leave create a resource.calendar.leaves
        calendar_leaves = self.env['resource.calendar.leaves'].search([
            ('time_type', '=', 'leave'),
            '|', ('company_id', 'in', employee_ids.mapped('company_id').ids),
                 ('company_id', '=', False),
            '|', ('resource_id', 'in', employee_ids.mapped('resource_id').ids),
                 ('resource_id', '=', False),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
        ], order='date_from')

        leaves = defaultdict(list)
        for leave in calendar_leaves:
            for employee in employee_ids:
                if (not leave.company_id or leave.company_id == employee.company_id) and\
                   (not leave.resource_id or leave.resource_id == employee.resource_id) and\
                   (not leave.calendar_id or leave.calendar_id == employee.resource_calendar_id):
                    leaves[employee.id].append(leave)

        # Get non-validated time off
        leaves_query = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids.ids),
            ('state', 'in', ['confirm', 'validate1']),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from)
        ], order='date_from')
        for leave in leaves_query:
            leaves[leave.employee_id.id].append(leave)
        return leaves

    def _get_leave_warning_parameters(self, leaves, employee, date_from, date_to):
        loc_cache = {}

        def localize(date):
            if date not in loc_cache:
                loc_cache[date] = utc.localize(date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None)
            return loc_cache[date]

        periods = self._group_leaves(leaves, employee, date_from, date_to)
        periods_by_states = [list(b) for a, b in groupby(periods, key=lambda x: x['is_validated'])]
        res = {}
        for periods in periods_by_states:
            leaves_for_employee = {'name': employee.name, "leaves": []}
            for period in periods:
                dfrom = period['from']
                dto = period['to']
                number_of_days = period['number_of_days']
                if number_of_days == 1:
                    leaves_for_employee['leaves'].append({
                        "start_date": format_date(self.env, localize(dfrom)),
                    })
                elif number_of_days < 1:
                    leaves_for_employee['leaves'].append({
                        "start_date": format_date(self.env, localize(dfrom)),
                        "start_time": convert_time_to_string(self.env, localize(dfrom), 'short'),
                        "end_time": convert_time_to_string(self.env, localize(dto), 'short')
                    })
                else:
                    leaves_for_employee['leaves'].append({
                        "start_date": format_date(self.env, localize(dfrom)),
                        "end_date": format_date(self.env, localize(dto)),
                    })
            res["validated" if periods[0].get('is_validated') else "requested"] = leaves_for_employee
        return res

    def format_date_range_to_string(self, date_dict):
        if len(date_dict) == 3:
            return _('on %(start_date)s from %(start_time)s to %(end_time)s', **date_dict)
        elif len(date_dict) == 2:
            return _('from %(start_date)s to %(end_date)s', **date_dict)
        else:
            return _('on %(start_date)s', **date_dict)

    def _get_leave_warning(self, leaves, employee, date_from, date_to):
        leaves_parameters = self._get_leave_warning_parameters(leaves, employee, date_from, date_to)
        warning = ''
        for leave_type, leaves_for_employee in leaves_parameters.items():
            if not leaves_for_employee:
                continue
            if leave_type == "validated":
                warning += _(
                    '%(name)s is on time off %(leaves)s. \n',
                    name=leaves_for_employee["name"],
                    leaves=', '.join(map(self.format_date_range_to_string, leaves_for_employee["leaves"]))
                )
            else:
                warning += _(
                    '%(name)s requested time off %(leaves)s. \n',
                    name=leaves_for_employee["name"],
                    leaves=', '.join(map(self.format_date_range_to_string, leaves_for_employee["leaves"]))
                )
        return warning

    def _group_leaves(self, leaves, employee_id, date_from, date_to):
        """
            Returns all the leaves happening between `planned_date_begin` and `date_deadline`
        """
        work_times = {wk[0]: wk[1] for wk in employee_id._list_work_time_per_day(date_from, date_to)[employee_id.id]}

        def has_working_hours(start_dt, end_dt):
            """
                Returns `True` if there are any working days between `start_dt` and `end_dt`.
            """
            diff_days = (end_dt - start_dt).days
            all_dates = [start_dt.date() + timedelta(days=delta) for delta in range(diff_days + 1)]
            return any(d in work_times for d in all_dates)

        periods = []
        for leave in leaves:
            if leave.date_from > date_to or leave.date_to < date_from:
                continue

            # Can handle both hr.leave and resource.calendar.leaves
            number_of_days = 0
            is_validated = True
            if isinstance(leave, self.pool['hr.leave']):
                number_of_days = leave.number_of_days
                is_validated = False
            else:
                dt_delta = (leave.date_to - leave.date_from)
                if leave.holiday_id and not (leave.holiday_id.sudo().request_unit_half or leave.holiday_id.sudo().request_unit_hours):
                    number_of_days = dt_delta.days + 1
                else:
                    number_of_days = dt_delta.days + ((dt_delta.seconds / 3600) / 24)
            # leaves are ordered by date_from and grouped by type. When go from the batch of validated time offs to the
            # requested ones, we need to bypass the second condition with the third one
            if not periods or has_working_hours(periods[-1]['from'], leave.date_to) or \
                    periods[-1]['is_validated'] != is_validated:
                periods.append({'is_validated': is_validated, 'from': leave.date_from, 'to': leave.date_to, 'number_of_days': number_of_days})
            else:
                periods[-1]['is_validated'] = is_validated
                if periods[-1]['to'] < leave.date_to:
                    periods[-1]['to'] = leave.date_to
                periods[-1]['number_of_days'] = periods[-1].get('number_of_days') or number_of_days
        return periods

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        if field != "employee_id":
            return super()._gantt_unavailability(field, res_ids, start, stop, scale)

        employees = self.env['hr.employee'].browse(res_ids)
        leaves_mapping = employees.resource_id._get_unavailable_intervals(start, stop)

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        result = {}
        for employee in employees:
            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, leaves_mapping.get(employee.resource_id.id, []))
            result[employee.id] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
        return result

def tag_employee_rows(rows):
    """
        Add `employee_id` key in rows and subsrows recursively if necessary
        :return: a set of ids with all concerned employees (subrows included)
    """
    employee_ids = set()
    for row in rows:
        group_bys = row.get('groupedBy')
        res_id = row.get('resId')
        if group_bys:
            # if employee_id is the first grouping attribute, we mark the row
            if group_bys[0] == 'employee_id' and res_id:
                employee_id = res_id
                employee_ids.add(employee_id)
                row['employee_id'] = employee_id
            # else we recursively traverse the rows where employee_id appears in the group_by
            elif 'employee_id' in group_bys:
                employee_ids.update(tag_employee_rows(row.get('rows')))
    return employee_ids

# function to recursively replace subrows with the ones returned by func
def traverse(func, row):
    new_row = dict(row)
    if new_row.get('employee_id'):
        for sub_row in new_row.get('rows'):
            sub_row['employee_id'] = new_row['employee_id']
    new_row['rows'] = [traverse(func, row) for row in new_row.get('rows')]
    return func(new_row)
