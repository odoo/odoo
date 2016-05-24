# -*- coding: utf-8 -*-
import datetime
import time

from dateutil.relativedelta import relativedelta
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

import openerp
from openerp.osv import osv
from openerp import SUPERUSER_ID, tools


class hr_department(models.Model):
    _inherit = 'hr.department'

    @api.multi
    def _compute_leave_count(self):
        Holiday = self.env['hr.holidays']
        today_date = datetime.datetime.utcnow().date()
        today_start = today_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT) # get the midnight of the current utc day
        today_end = (today_date + relativedelta(hours=23, minutes=59, seconds=59)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        leave_data = Holiday.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm'), ('type', '=', 'remove')],
            ['department_id'], ['department_id'])
        allocation_data = Holiday.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm'), ('type', '=', 'add')],
            ['department_id'], ['department_id'])
        absence_data = Holiday.read_group(
            [('department_id', 'in', self.ids), ('state', 'not in', ['cancel', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start), ('type', '=', 'remove')],
            ['department_id'], ['department_id'])

        res_leave = dict((data['department_id'][0], data['department_id_count']) for data in leave_data)
        res_allocation = dict((data['department_id'][0], data['department_id_count']) for data in allocation_data)
        res_absence = dict((data['department_id'][0], data['department_id_count']) for data in absence_data)

        for department in self:
            department.leave_to_approve_count = res_leave.get(department.id, 0)
            department.allocation_to_approve_count = res_allocation.get(department.id, 0)
            department.absence_of_today = res_absence.get(department.id, 0)


    @api.multi
    def _compute_total_employee(self):
        emp_data = self.env['hr.employee'].read_group([('department_id', 'in', self.ids)], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in emp_data)
        for department in self:
            department.total_employee = result.get(department.id, 0)

    absence_of_today = fields.Integer(
        compute='_compute_leave_count', string='Absence by Today')
    leave_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Leave to Approve')
    allocation_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Allocation to Approve')
    total_employee = fields.Integer(
        compute='_compute_total_employee', string='Total Employee')


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
        #Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays_id = holidays_obj.search(cr, SUPERUSER_ID,
           [('employee_id', 'in', ids), ('date_from','<=',time.strftime('%Y-%m-%d %H:%M:%S')),
           ('date_to','>=',time.strftime('%Y-%m-%d %H:%M:%S')),('type','=','remove'),('state','not in',('cancel','refuse'))],
           context=context)
        result = {}
        for id in ids:
            result[id] = {
                'current_leave_state': False,
                'current_leave_id': False,
                'leave_date_from':False,
                'leave_date_to':False,
            }
        for holiday in self.pool.get('hr.holidays').browse(cr, SUPERUSER_ID, holidays_id, context=context):
            result[holiday.employee_id.id]['leave_date_from'] = holiday.date_from
            result[holiday.employee_id.id]['leave_date_to'] = holiday.date_to
            result[holiday.employee_id.id]['current_leave_state'] = holiday.state
            result[holiday.employee_id.id]['current_leave_id'] = holiday.holiday_status_id.id
        return result

    def _leaves_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        leaves = self.pool['hr.holidays'].read_group(cr, uid, [
            ('employee_id', 'in', ids),
            ('holiday_status_id.limit', '=', False), ('state', '=', 'validate')], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        res.update(dict([(leave['employee_id'][0], leave['number_of_days']) for leave in leaves ]))
        return res

    def _show_approved_remaining_leave(self, cr, uid, ids, name, args, context=None):
        if self.pool['res.users'].has_group(cr, uid, 'base.group_hr_user'):
            return dict([(employee_id, True) for employee_id in ids])
        return dict([(employee.id, True) for employee in self.browse(cr, uid, ids, context=context) if employee.user_id.id == uid])

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
        'remaining_leaves': openerp.osv.fields.function(_get_remaining_days, string='Remaining Legal Leaves', fnct_inv=_set_remaining_days, type="float", help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. Total based on all the leave types without overriding limit.'),
        'current_leave_state': openerp.osv.fields.function(
            _get_leave_status, multi="leave_status", string="Current Leave Status", type="selection",
            selection=[('draft', 'New'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
                       ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')]),
        'current_leave_id': openerp.osv.fields.function(_get_leave_status, multi="leave_status", string="Current Leave Type", type='many2one', relation='hr.holidays.status'),
        'leave_date_from': openerp.osv.fields.function(_get_leave_status, multi='leave_status', type='date', string='From Date'),
        'leave_date_to': openerp.osv.fields.function(_get_leave_status, multi='leave_status', type='date', string='To Date'),
        'leaves_count': openerp.osv.fields.function(_leaves_count, type='integer', string='Number of Leaves'),
        'show_leaves': openerp.osv.fields.function(_show_approved_remaining_leave, type='boolean', string="Able to see Remaining Leaves"),
        'is_absent_totay': openerp.osv.fields.function(_absent_employee, fnct_search=_search_absent_employee, type="boolean", string="Absent Today", default=False)
    }
