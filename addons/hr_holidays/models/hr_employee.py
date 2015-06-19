# -*- coding: utf-8 -*-

import calendar
import datetime
from datetime import date
import time

from dateutil.relativedelta import relativedelta

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _


class hr_employee(osv.Model):
    _inherit = "hr.employee"

    def _set_remaining_days(self, cr, uid, empl_id, name, value, arg, context=None):
        if value:
            employee = self.browse(cr, uid, empl_id, context=context)
            diff = value - employee.remaining_leaves
            type_obj = self.pool.get('hr.holidays.status')
            holiday_obj = self.pool.get('hr.holidays')
            # Find for holidays status
            status_ids = type_obj.search(cr, uid, [('limit', '=', False)], context=context)
            if len(status_ids) != 1 :
                raise osv.except_osv(_('Warning!'),_("The feature behind the field 'Remaining Legal Leaves' can only be used when there is only one leave type with the option 'Allow to Override Limit' unchecked. (%s Found). Otherwise, the update is ambiguous as we cannot decide on which leave type the update has to be done. \nYou may prefer to use the classic menus 'Leave Requests' and 'Allocation Requests' located in 'Human Resources \ Leaves' to manage the leave days of the employees if the configuration does not allow to use this field.") % (len(status_ids)))
            status_id = status_ids and status_ids[0] or False
            if not status_id:
                return False
            if diff > 0:
                leave_id = holiday_obj.create(cr, uid, {'name': _('Allocation for %s') % employee.name, 'employee_id': employee.id, 'holiday_status_id': status_id, 'type': 'add', 'holiday_type': 'employee', 'number_of_days_temp': diff}, context=context)
            elif diff < 0:
                raise osv.except_osv(_('Warning!'), _('You cannot reduce validated allocation requests'))
            else:
                return False
            for sig in ('confirm', 'validate', 'second_validate'):
                holiday_obj.signal_workflow(cr, uid, [leave_id], sig)
            return True
        return False

    def _get_remaining_days(self, cr, uid, ids, name, args, context=None):
        cr.execute("""SELECT
                sum(h.number_of_days) as days,
                h.employee_id
            from
                hr_holidays h
                join hr_holidays_status s on (s.id=h.holiday_status_id)
            where
                h.state='validate' and
                s.limit=False and
                h.employee_id in %s
            group by h.employee_id""", (tuple(ids),))
        res = cr.dictfetchall()
        remaining = {}
        for r in res:
            remaining[r['employee_id']] = r['days']
        for employee_id in ids:
            if not remaining.get(employee_id):
                remaining[employee_id] = 0.0
        return remaining

    def _get_leave_status(self, cr, uid, ids, name, args, context=None):
        holidays_obj = self.pool.get('hr.holidays')
        holidays_id = holidays_obj.search(cr, uid,
           [('employee_id', 'in', ids), ('date_from','<=',time.strftime('%Y-%m-%d %H:%M:%S')),
           ('date_to','>=',time.strftime('%Y-%m-%d 23:59:59')),('type','=','remove'),('state','not in',('cancel','refuse'))],
           context=context)
        result = {}
        for id in ids:
            result[id] = {
                'current_leave_state': False,
                'current_leave_id': False,
                'leave_date_from':False,
                'leave_date_to':False,
            }
        for holiday in self.pool.get('hr.holidays').browse(cr, uid, holidays_id, context=context):
            result[holiday.employee_id.id]['leave_date_from'] = holiday.date_from
            result[holiday.employee_id.id]['leave_date_to'] = holiday.date_to
            result[holiday.employee_id.id]['current_leave_state'] = holiday.state
            result[holiday.employee_id.id]['current_leave_id'] = holiday.holiday_status_id.id
        return result

    def _leaves_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        Holidays = self.pool['hr.holidays']
        date_begin = date.today().replace(day=1)
        date_end = date_begin.replace(day=calendar.monthrange(date_begin.year, date_begin.month)[1])
        for employee_id in ids:
            leaves = Holidays.search_count(cr, uid, [('employee_id', '=', employee_id), ('type', '=', 'remove')], context=context)
            approved_leaves = Holidays.search_count(cr, uid, [('employee_id', '=', employee_id), ('type', '=', 'remove'), ('date_from', '>=', date_begin.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)), ('date_from', '<=', date_end.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)), ('state', '=', 'validate'), ('payslip_status', '=', False)], context=context)
            res[employee_id] = {'leaves_count': leaves, 'approved_leaves_count': approved_leaves}
        return res

    def _absent_employee(self, cr, uid, ids, field_name, arg, context=None):
        today_date = datetime.datetime.utcnow().date()
        today_start = today_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT) # get the midnight of the current utc day
        today_end = (today_date + relativedelta(hours=23, minutes=59, seconds=59)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        data = self.pool['hr.holidays'].read_group(cr, uid,
            [('employee_id', 'in', ids), ('state', 'not in', ['cancel', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start), ('type', '=', 'remove')],
            ['employee_id'], ['employee_id'], context=context)
        result = dict.fromkeys(ids, False)
        for d in data:
            if d['employee_id_count'] >= 1:
                result[d['employee_id'][0]] = True
        return result

    def _search_absent_employee(self, cr, uid, obj, name, args, context=None):
        today_date = datetime.datetime.utcnow().date()
        today_start = today_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT) # get the midnight of the current utc day
        today_end = (today_date + relativedelta(hours=23, minutes=59, seconds=59)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        holiday_ids = self.pool['hr.holidays'].search_read(cr, uid, [
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
            ('type', '=', 'remove')], ['employee_id'], context=context)
        absent_employee_ids = [holiday['employee_id'][0] for holiday in holiday_ids if holiday['employee_id']]
        return [('id', 'in', absent_employee_ids)]

    _columns = {
        'remaining_leaves': fields.function(_get_remaining_days, string='Remaining Legal Leaves', fnct_inv=_set_remaining_days, type="float", help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. Total based on all the leave types without overriding limit.'),
        'current_leave_state': fields.function(
            _get_leave_status, multi="leave_status", string="Current Leave Status", type="selection",
            selection=[('draft', 'New'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
                       ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')]),
        'current_leave_id': fields.function(_get_leave_status, multi="leave_status", string="Current Leave Type", type='many2one', relation='hr.holidays.status'),
        'leave_date_from': fields.function(_get_leave_status, multi='leave_status', type='date', string='From Date'),
        'leave_date_to': fields.function(_get_leave_status, multi='leave_status', type='date', string='To Date'),
        'leaves_count': fields.function(_leaves_count, multi='_leaves_count', type='integer', string='Number of Leaves (current month)'),
        'approved_leaves_count': fields.function(_leaves_count, multi='_leaves_count', type='integer', string='Approved Leaves not in Payslip', help="These leaves are approved but not taken into account for payslip"),
        'is_absent_totay': fields.function(_absent_employee, fnct_search=_search_absent_employee, type="boolean", string="Absent Today", default=False)
    }
