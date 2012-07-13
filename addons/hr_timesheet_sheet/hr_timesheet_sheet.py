# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from osv import fields, osv
from tools.translate import _
import netsvc

class one2many_mod2(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}

        if values is None:
            values = {}

        # res6 = {id: date_current, ...}
        res6 = dict([(rec['id'], rec['date_current'])
            for rec in obj.read(cr, user, ids, ['date_current'], context=context)])

        dom = []
        for c, id in enumerate(ids):
            if id in res6:
                if c: # skip first
                    dom.insert(0 ,'|')
                dom.append('&')
                dom.append('&')
                dom.append(('name', '>=', res6[id]))
                dom.append(('name', '<=', res6[id]))
                dom.append(('sheet_id', '=', id))

        ids2 = obj.pool.get(self._obj).search(cr, user, dom, limit=self._limit)

        res = {}
        for i in ids:
            res[i] = []

        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_read'):
            if r[self._fields_id]:
                res[r[self._fields_id][0]].append(r['id'])
        return res

    def set(self, cr, obj, id, field, values, user=None, context=None):
        if context is None:
            context = {}

        context = context.copy()
        context['sheet_id'] = id
        return super(one2many_mod2, self).set(cr, obj, id, field, values, user=user, context=context)


class one2many_mod(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}

        if values is None:
            values = {}


        res5 = obj.read(cr, user, ids, ['date_current'], context=context)
        res6 = {}
        for r in res5:
            res6[r['id']] = r['date_current']

        ids2 = []
        for id in ids:
            dom = []
            if id in res6:
                dom = [('date', '=', res6[id]), ('sheet_id', '=', id)]
            ids2.extend(obj.pool.get(self._obj).search(cr, user,
                dom, limit=self._limit))
        res = {}
        for i in ids:
            res[i] = []
        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2,
                [self._fields_id], context=context, load='_classic_read'):
            if r[self._fields_id]:
                res[r[self._fields_id][0]].append(r['id'])

        return res

class hr_timesheet_sheet(osv.osv):
    _name = "hr_timesheet_sheet.sheet"
    _table = 'hr_timesheet_sheet_sheet'
    _order = "id desc"
    _description="Timesheet"

    def _total_attendances(self, cr, uid, ids, name, args, context=None):
        """ Get the total attendance for the timesheets
            Returns a dict like :
                {id: {'date_current': '2011-06-17',
                      'total_per_day': {day: timedelta, ...},
                     },
                 ...
                }
        """
        context = context or {}
        attendance_obj = self.pool.get('hr.attendance')
        res = {}
        for sheet_id in ids:
            sheet = self.browse(cr, uid, sheet_id, context=context)
            date_current = sheet.date_current
            # field attendances_ids of hr_timesheet_sheet.sheet only
            # returns attendances of timesheet's current date
            attendance_ids = attendance_obj.search(cr, uid, [('sheet_id', '=', sheet_id)], context=context)
            attendances = attendance_obj.browse(cr, uid, attendance_ids, context=context)
            total_attendance = {}
            for attendance in [att for att in attendances
                               if att.action in ('sign_in', 'sign_out')]:
                day = attendance.name[:10]
                if not total_attendance.get(day, False):
                    total_attendance[day] = timedelta(seconds=0)

                attendance_in_time = datetime.strptime(attendance.name, '%Y-%m-%d %H:%M:%S')
                attendance_interval = timedelta(hours=attendance_in_time.hour,
                                                minutes=attendance_in_time.minute,
                                                seconds=attendance_in_time.second)
                if attendance.action == 'sign_in':
                    total_attendance[day] -= attendance_interval
                else:
                    total_attendance[day] += attendance_interval

                # if the delta is negative, it means that a sign out is missing
                # in a such case, we want to have the time to the end of the day
                # for a past date, and the time to now for the current date
                if total_attendance[day] < timedelta(0):
                    if day == date_current:
                        now = datetime.now()
                        total_attendance[day] += timedelta(hours=now.hour,
                                                           minutes=now.minute,
                                                           seconds=now.second)
                    else:
                        total_attendance[day] += timedelta(days=1)

            res[sheet_id] = {'date_current': date_current,
                             'total_per_day': total_attendance}
        return res

    def _total_timesheet(self, cr, uid, ids, name, args, context=None):
        """ Get the total of analytic lines for the timesheets
            Returns a dict like :
                {id: {day: timedelta, ...}}
        """
        context = context or {}
        sheet_line_obj = self.pool.get('hr.analytic.timesheet')

        res = {}
        for sheet_id in ids:
            # field timesheet_ids of hr_timesheet_sheet.sheet only
            # returns lines of timesheet's current date
            sheet_lines_ids = sheet_line_obj.search(cr, uid, [('sheet_id', '=', sheet_id)], context=context)
            sheet_lines = sheet_line_obj.browse(cr, uid, sheet_lines_ids, context=context)
            total_timesheet = {}
            for line in sheet_lines:
                day = line.date
                if not total_timesheet.get(day, False):
                    total_timesheet[day] = timedelta(seconds=0)
                total_timesheet[day] += timedelta(hours=line.unit_amount)
            res[sheet_id] = total_timesheet
        return res

    def _total(self, cr, uid, ids, name, args, context=None):
        """ Compute the attendances, analytic lines timesheets and differences between them
            for all the days of a timesheet and the current day
        """
        def sum_all_days(sheet_amounts):
            if not sheet_amounts:
                return timedelta(seconds=0)
            total = reduce(lambda memo, value: memo + value, sheet_amounts.values())
            return total

        def timedelta_to_hours(delta):
            hours = 0.0
            seconds = float(delta.seconds)
            if delta.microseconds:
                seconds += float(delta.microseconds) / 100000
            hours += delta.days * 24
            if seconds:
                hours += seconds / 3600
            return hours

        res = {}
        all_timesheet_attendances = self._total_attendances(cr, uid, ids, name, args, context=context)
        all_timesheet_lines = self._total_timesheet(cr, uid, ids, name, args, context=context)
        for id in ids:
            res[id] = {}

            all_attendances_sheet = all_timesheet_attendances[id]

            date_current = all_attendances_sheet['date_current']
            total_attendances_sheet = all_attendances_sheet['total_per_day']
            total_attendances_all_days = sum_all_days(total_attendances_sheet)
            total_attendances_day = total_attendances_sheet.get(date_current, timedelta(seconds=0))

            total_timesheets_sheet = all_timesheet_lines[id]
            total_timesheets_all_days = sum_all_days(total_timesheets_sheet)
            total_timesheets_day = total_timesheets_sheet.get(date_current, timedelta(seconds=0))
            total_difference_all_days = total_attendances_all_days - total_timesheets_all_days
            total_difference_day = total_attendances_day - total_timesheets_day

            res[id]['total_attendance'] = timedelta_to_hours(total_attendances_all_days)
            res[id]['total_timesheet'] = timedelta_to_hours(total_timesheets_all_days)
            res[id]['total_difference'] = timedelta_to_hours(total_difference_all_days)

            res[id]['total_attendance_day'] = timedelta_to_hours(total_attendances_day)
            res[id]['total_timesheet_day'] = timedelta_to_hours(total_timesheets_day)
            res[id]['total_difference_day'] = timedelta_to_hours(total_difference_day)
        return res

    def check_employee_attendance_state(self, cr, uid, sheet_id, context=None):
        ids_signin = self.pool.get('hr.attendance').search(cr,uid,[('sheet_id', '=', sheet_id),('action','=','sign_in')])
        ids_signout = self.pool.get('hr.attendance').search(cr,uid,[('sheet_id', '=', sheet_id),('action','=','sign_out')])

        if len(ids_signin) != len(ids_signout):
            raise osv.except_osv(('Warning !'),_('The timesheet cannot be validated as it does not contain an equal number of sign ins and sign outs!'))
        return True

    def copy(self, cr, uid, ids, *args, **argv):
        raise osv.except_osv(_('Error !'), _('You cannot duplicate a timesheet!'))

    def create(self, cr, uid, vals, *args, **argv):
        if 'employee_id' in vals:
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).user_id:
                raise osv.except_osv(_('Error !'), _('In order to create a timesheet for this employee, you must assign it to a user!'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).product_id:
                raise osv.except_osv(_('Error !'), _('In order to create a timesheet for this employee, you must link the employee to a product, like \'Consultant\'!'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).journal_id:
                raise osv.except_osv(_('Error !'), _('In order to create a timesheet for this employee, you must assign the employee to an analytic journal, like \'Timesheet\'!'))
        return super(hr_timesheet_sheet, self).create(cr, uid, vals, *args, **argv)

    def write(self, cr, uid, ids, vals, *args, **argv):
        if 'employee_id' in vals:
            new_user_id = self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).user_id.id or False
            if not new_user_id:
                raise osv.except_osv(_('Error !'), _('In order to create a timesheet for this employee, you must assign it to a user!'))
            if not self._sheet_date(cr, uid, ids, forced_user_id=new_user_id):
                raise osv.except_osv(_('Error !'), _('You cannot have 2 timesheets that overlaps!\nYou should use the menu \'My Timesheet\' to avoid this problem.'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).product_id:
                raise osv.except_osv(_('Error !'), _('In order to create a timesheet for this employee, you must link the employee to a product!'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).journal_id:
                raise osv.except_osv(_('Error !'), _('In order to create a timesheet for this employee, you must assign the employee to an analytic journal!'))
        return super(hr_timesheet_sheet, self).write(cr, uid, ids, vals, *args, **argv)

    def button_confirm(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            self.check_employee_attendance_state(cr, uid, sheet.id, context=context)
            di = sheet.user_id.company_id.timesheet_max_difference
            if (abs(sheet.total_difference) < di) or not di:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'hr_timesheet_sheet.sheet', sheet.id, 'confirm', cr)
            else:
                raise osv.except_osv(_('Warning !'), _('Please verify that the total difference of the sheet is lower than %.2f !') %(di,))
        return True

    def date_today(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if datetime.today() <= datetime.strptime(sheet.date_from, '%Y-%m-%d'):
                self.write(cr, uid, [sheet.id], {'date_current': sheet.date_from,}, context=context)
            elif datetime.now() >= datetime.strptime(sheet.date_to, '%Y-%m-%d'):
                self.write(cr, uid, [sheet.id], {'date_current': sheet.date_to,}, context=context)
            else:
                self.write(cr, uid, [sheet.id], {'date_current': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def date_previous(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if datetime.strptime(sheet.date_current, '%Y-%m-%d') <= datetime.strptime(sheet.date_from, '%Y-%m-%d'):
                self.write(cr, uid, [sheet.id], {'date_current': sheet.date_from,}, context=context)
            else:
                self.write(cr, uid, [sheet.id], {
                    'date_current': (datetime.strptime(sheet.date_current, '%Y-%m-%d') + relativedelta(days=-1)).strftime('%Y-%m-%d'),
                }, context=context)
        return True

    def date_next(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if datetime.strptime(sheet.date_current, '%Y-%m-%d') >= datetime.strptime(sheet.date_to, '%Y-%m-%d'):
                self.write(cr, uid, [sheet.id], {'date_current': sheet.date_to,}, context=context)
            else:
                self.write(cr, uid, [sheet.id], {
                    'date_current': (datetime.strptime(sheet.date_current, '%Y-%m-%d') + relativedelta(days=1)).strftime('%Y-%m-%d'),
                }, context=context)
        return True

    def button_dummy(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if datetime.strptime(sheet.date_current, '%Y-%m-%d') <= datetime.strptime(sheet.date_from, '%Y-%m-%d'):
                self.write(cr, uid, [sheet.id], {'date_current': sheet.date_from,}, context=context)
            elif datetime.strptime(sheet.date_current, '%Y-%m-%d') >= datetime.strptime(sheet.date_to, '%Y-%m-%d'):
                self.write(cr, uid, [sheet.id], {'date_current': sheet.date_to,}, context=context)
        return True

    def check_sign(self, cr, uid, ids, typ, context=None):
        sheet = self.browse(cr, uid, ids, context=context)[0]
        if not sheet.date_current == time.strftime('%Y-%m-%d'):
            raise osv.except_osv(_('Error !'), _('You cannot sign in/sign out from an other date than today.'))
        return True

    def sign(self, cr, uid, ids, typ, context=None):
        self.check_sign(cr, uid, ids, typ, context=context)
        sign_obj = self.pool.get('hr.sign.in.out')
        sheet = self.browse(cr, uid, ids, context=context)[0]
        context['emp_id'] = [sheet.employee_id.id]
        sign_id = sign_obj.create(cr, uid, {}, context=context)
        methods = {'sign_in': sign_obj.si_check,
                   'sign_out': sign_obj.so_check}
        wizard_result = methods[typ](cr, uid, [sign_id], context=context)
        if wizard_result.get('type', False) == 'ir.actions.act_window_close':
            return True  # ensure we do not close the main window !
        wizard_result['nodestroy'] = True  # do not destroy the main window !
        return wizard_result

    def sign_in(self, cr, uid, ids, context=None):
        return self.sign(cr, uid, ids, 'sign_in', context=context)

    def sign_out(self, cr, uid, ids, context=None):
        return self.sign(cr, uid, ids, 'sign_out', context=context)

    _columns = {
        'name': fields.char('Note', size=64, select=1,
                            states={'confirm':[('readonly', True)], 'done':[('readonly', True)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'user_id': fields.related('employee_id', 'user_id', type="many2one", relation="res.users", store=True, string="User", required=False, readonly=True),#fields.many2one('res.users', 'User', required=True, select=1, states={'confirm':[('readonly', True)], 'done':[('readonly', True)]}),
        'date_from': fields.date('Date from', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}),
        'date_to': fields.date('Date to', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}),
        'date_current': fields.date('Current date', required=True, select=1),
        'timesheet_ids' : one2many_mod('hr.analytic.timesheet', 'sheet_id',
            'Timesheet lines', domain=[('date', '=', time.strftime('%Y-%m-%d'))],
            readonly=True, states={
                'draft': [('readonly', False)],
                'new': [('readonly', False)]}
            ),
        'attendances_ids' : one2many_mod2('hr.attendance', 'sheet_id', 'Attendances'),
        'state' : fields.selection([
            ('new', 'New'),
            ('draft','Open'),
            ('confirm','Waiting Approval'),
            ('done','Approved')], 'Status', select=True, required=True, readonly=True,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed timesheet. \
                \n* The \'Confirmed\' state is used for to confirm the timesheet by user. \
                \n* The \'Done\' state is used when users timesheet is accepted by his/her senior.'),
        'state_attendance' : fields.related('employee_id', 'state', type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Current Status', readonly=True),
        'total_attendance_day': fields.function(_total, method=True, string='Total Attendance', multi="_total"),
        'total_timesheet_day': fields.function(_total, method=True, string='Total Timesheet', multi="_total"),
        'total_difference_day': fields.function(_total, method=True, string='Difference', multi="_total"),
        'total_attendance': fields.function(_total, method=True, string='Total Attendance', multi="_total"),
        'total_timesheet': fields.function(_total, method=True, string='Total Timesheet', multi="_total"),
        'total_difference': fields.function(_total, method=True, string='Difference', multi="_total"),
        'period_ids': fields.one2many('hr_timesheet_sheet.sheet.day', 'sheet_id', 'Period', readonly=True),
        'account_ids': fields.one2many('hr_timesheet_sheet.sheet.account', 'sheet_id', 'Analytic accounts', readonly=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'department_id':fields.many2one('hr.department','Department'),
    }

    def _default_date_from(self,cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r=='month':
            return time.strftime('%Y-%m-01')
        elif r=='week':
            return (datetime.today() + relativedelta(weekday=0, days=-6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-01-01')
        return time.strftime('%Y-%m-%d')

    def _default_date_to(self,cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r=='month':
            return (datetime.today() + relativedelta(months=+1,day=1,days=-1)).strftime('%Y-%m-%d')
        elif r=='week':
            return (datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-12-31')
        return time.strftime('%Y-%m-%d')

    def _default_employee(self, cr, uid, context=None):
        emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id','=',uid)], context=context)
        return emp_ids and emp_ids[0] or False

    _defaults = {
        'date_from' : _default_date_from,
        'date_current' : lambda *a: time.strftime('%Y-%m-%d'),
        'date_to' : _default_date_to,
        'state': 'new',
        'employee_id': _default_employee,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'hr_timesheet_sheet.sheet', context=c)
    }

    def _sheet_date(self, cr, uid, ids, forced_user_id=False, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            new_user_id = forced_user_id or sheet.user_id and sheet.user_id.id
            if new_user_id:
                cr.execute('SELECT id \
                    FROM hr_timesheet_sheet_sheet \
                    WHERE (date_from <= %s and %s <= date_to) \
                        AND user_id=%s \
                        AND id <> %s',(sheet.date_to, sheet.date_from, new_user_id, sheet.id))
                if cr.fetchall():
                    return False
        return True

    def _date_current_check(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if sheet.date_current < sheet.date_from or sheet.date_current > sheet.date_to:
                return False
        return True


    _constraints = [
        (_sheet_date, 'You cannot have 2 timesheets that overlaps !\nPlease use the menu \'My Current Timesheet\' to avoid this problem.', ['date_from','date_to']),
        (_date_current_check, 'You must select a Current date which is in the timesheet dates !', ['date_current']),
    ]

    def action_set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService('workflow')
        for id in ids:
            wf_service.trg_create(uid, self._name, id, cr)
        return True

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        return [(r['id'], r['date_from'] + ' - ' + r['date_to']) \
                for r in self.read(cr, uid, ids, ['date_from', 'date_to'],
                    context=context, load='_classic_write')]

    def unlink(self, cr, uid, ids, context=None):
        sheets = self.read(cr, uid, ids, ['state','total_attendance'], context=context)
        for sheet in sheets:
            if sheet['state'] in ('confirm', 'done'):
                raise osv.except_osv(_('Invalid action !'), _('You cannot delete a timesheet which is already confirmed!'))
            elif sheet['total_attendance'] <> 0.00:
                raise osv.except_osv(_('Invalid action !'), _('You cannot delete a timesheet which have attendance entries!'))
        return super(hr_timesheet_sheet, self).unlink(cr, uid, ids, context=context)

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        department_id =  False
        if employee_id:
            department_id = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context).department_id.id
        return {'value': {'department_id': department_id}}

hr_timesheet_sheet()


class hr_timesheet_line(osv.osv):
    _inherit = "hr.analytic.timesheet"

    def _get_default_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'date' in context:
            return context['date']
        return time.strftime('%Y-%m-%d')

    def _sheet(self, cursor, user, ids, name, args, context=None):
        sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
        res = {}.fromkeys(ids, False)
        for ts_line in self.browse(cursor, user, ids, context=context):
            sheet_ids = sheet_obj.search(cursor, user,
                [('date_to', '>=', ts_line.date), ('date_from', '<=', ts_line.date),
                 ('employee_id.user_id', '=', ts_line.user_id.id)],
                context=context)
            if sheet_ids:
            # [0] because only one sheet possible for an employee between 2 dates
                res[ts_line.id] = sheet_obj.name_get(cursor, user, sheet_ids, context=context)[0]
        return res

    def _get_hr_timesheet_sheet(self, cr, uid, ids, context=None):
        ts_line_ids = []
        for ts in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                    SELECT l.id
                        FROM hr_analytic_timesheet l
                    INNER JOIN account_analytic_line al
                        ON (l.line_id = al.id)
                    WHERE %(date_to)s >= al.date
                        AND %(date_from)s <= al.date
                        AND %(user_id)s = al.user_id
                    GROUP BY l.id""", {'date_from': ts.date_from,
                                        'date_to': ts.date_to,
                                        'user_id': ts.employee_id.user_id.id,})
            ts_line_ids.extend([row[0] for row in cr.fetchall()])
        return ts_line_ids

    def _get_account_analytic_line(self, cr, uid, ids, context=None):
        ts_line_ids = self.pool.get('hr.analytic.timesheet').search(cr, uid, [('line_id', 'in', ids)])
        return ts_line_ids

    _columns = {
        'sheet_id': fields.function(_sheet, string='Sheet',
            type='many2one', relation='hr_timesheet_sheet.sheet',
            store={
                    'hr_timesheet_sheet.sheet': (_get_hr_timesheet_sheet, ['employee_id', 'date_from', 'date_to'], 10),
                    'account.analytic.line': (_get_account_analytic_line, ['user_id', 'date'], 10),
                    'hr.analytic.timesheet': (lambda self,cr,uid,ids,context=None: ids, None, 10),
                  },
            ),
    }
    _defaults = {
        'date': _get_default_date,
    }

    def _check_sheet_state(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for timesheet_line in self.browse(cr, uid, ids, context=context):
            if timesheet_line.sheet_id and timesheet_line.sheet_id.state not in ('draft', 'new'):
                return False
        return True

    _constraints = [
        (_check_sheet_state, 'You cannot modify an entry in a Confirmed/Done timesheet !.', ['state']),
    ]

    def unlink(self, cr, uid, ids, *args, **kwargs):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        return super(hr_timesheet_line,self).unlink(cr, uid, ids,*args, **kwargs)

    def _check(self, cr, uid, ids):
        for att in self.browse(cr, uid, ids):
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error !'), _('You can not modify an entry in a confirmed timesheet !'))
        return True

hr_timesheet_line()

class hr_attendance(osv.osv):
    _inherit = "hr.attendance"

    def _get_default_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'name' in context:
            return context['name'] + time.strftime(' %H:%M:%S')
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def _get_hr_timesheet_sheet(self, cr, uid, ids, context=None):
        attendance_ids = []
        for ts in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                        SELECT a.id
                          FROM hr_attendance a
                         INNER JOIN hr_employee e
                               INNER JOIN resource_resource r
                                       ON (e.resource_id = r.id)
                            ON (a.employee_id = e.id)
                        WHERE %(date_to)s >= date_trunc('day', a.name)
                              AND %(date_from)s <= a.name
                              AND %(user_id)s = r.user_id
                         GROUP BY a.id""", {'date_from': ts.date_from,
                                            'date_to': ts.date_to,
                                            'user_id': ts.employee_id.user_id.id,})
            attendance_ids.extend([row[0] for row in cr.fetchall()])
        return attendance_ids

    def _sheet(self, cursor, user, ids, name, args, context=None):
        sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
        res = {}.fromkeys(ids, False)
        for attendance in self.browse(cursor, user, ids, context=context):
            date_to = datetime.strftime(datetime.strptime(attendance.name[0:10], '%Y-%m-%d'), '%Y-%m-%d %H:%M:%S')
            sheet_ids = sheet_obj.search(cursor, user,
                [('date_to', '>=', date_to), ('date_from', '<=', attendance.name),
                 ('employee_id', '=', attendance.employee_id.id)],
                context=context)
            if sheet_ids:
                # [0] because only one sheet possible for an employee between 2 dates
                res[attendance.id] = sheet_obj.name_get(cursor, user, sheet_ids, context=context)[0]
        return res

    _columns = {
        'sheet_id': fields.function(_sheet, string='Sheet',
            type='many2one', relation='hr_timesheet_sheet.sheet',
            store={
                      'hr_timesheet_sheet.sheet': (_get_hr_timesheet_sheet, ['employee_id', 'date_from', 'date_to'], 10),
                      'hr.attendance': (lambda self,cr,uid,ids,context=None: ids, ['employee_id', 'name', 'day'], 10),
                  },
            )
    }
    _defaults = {
        'name': _get_default_date,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'sheet_id' in context:
            ts = self.pool.get('hr_timesheet_sheet.sheet').browse(cr, uid, context['sheet_id'], context=context)
            if ts.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error !'), _('You cannot modify an entry in a confirmed timesheet !'))
        res = super(hr_attendance,self).create(cr, uid, vals, context=context)
        if 'sheet_id' in context:
            if context['sheet_id'] != self.browse(cr, uid, res, context=context).sheet_id.id:
                raise osv.except_osv(_('UserError'), _('You cannot enter an attendance ' \
                        'date outside the current timesheet dates!'))
        return res

    def unlink(self, cr, uid, ids, *args, **kwargs):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        return super(hr_attendance,self).unlink(cr, uid, ids,*args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        res = super(hr_attendance,self).write(cr, uid, ids, vals, context=context)
        if 'sheet_id' in context:
            for attendance in self.browse(cr, uid, ids, context=context):
                if context['sheet_id'] != attendance.sheet_id.id:
                    raise osv.except_osv(_('UserError'), _('You cannot enter an attendance ' \
                            'date outside the current timesheet dates!'))
        return res

    def _check(self, cr, uid, ids):
        for att in self.browse(cr, uid, ids):
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error !'), _('You cannot modify an entry in a confirmed timesheet !'))
        return True

hr_attendance()

class hr_timesheet_sheet_sheet_day(osv.osv):
    _name = "hr_timesheet_sheet.sheet.day"
    _description = "Timesheets by Period"
    _auto = False
    _order='name'
    _columns = {
        'name': fields.date('Date', readonly=True),
        'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True, select="1"),
        'total_timesheet': fields.float('Total Timesheet', readonly=True),
        'total_attendance': fields.float('Attendance', readonly=True),
        'total_difference': fields.float('Difference', readonly=True),
    }

    def init(self, cr):
        cr.execute("""create or replace view hr_timesheet_sheet_sheet_day as
            SELECT
                id,
                name,
                sheet_id,
                total_timesheet,
                total_attendance,
                cast(round(cast(total_attendance - total_timesheet as Numeric),2) as Double Precision) AS total_difference
            FROM
                ((
                    SELECT
                        MAX(id) as id,
                        name,
                        sheet_id,
                        SUM(total_timesheet) as total_timesheet,
                        CASE WHEN SUM(total_attendance) < 0
                            THEN (SUM(total_attendance) +
                                CASE WHEN current_date <> name
                                    THEN 1440
                                    ELSE (EXTRACT(hour FROM current_time) * 60) + EXTRACT(minute FROM current_time)
                                END
                                )
                            ELSE SUM(total_attendance)
                        END /60  as total_attendance
                    FROM
                        ((
                            select
                                min(hrt.id) as id,
                                l.date::date as name,
                                s.id as sheet_id,
                                sum(l.unit_amount) as total_timesheet,
                                0.0 as total_attendance
                            from
                                hr_analytic_timesheet hrt
                                left join (account_analytic_line l
                                    LEFT JOIN hr_timesheet_sheet_sheet s
                                    ON (s.date_to >= l.date
                                        AND s.date_from <= l.date
                                        AND s.user_id = l.user_id))
                                    on (l.id = hrt.line_id)
                            group by l.date::date, s.id
                        ) union (
                            select
                                -min(a.id) as id,
                                a.name::date as name,
                                s.id as sheet_id,
                                0.0 as total_timesheet,
                                SUM(((EXTRACT(hour FROM a.name) * 60) + EXTRACT(minute FROM a.name)) * (CASE WHEN a.action = 'sign_in' THEN -1 ELSE 1 END)) as total_attendance
                            from
                                hr_attendance a
                                LEFT JOIN (hr_timesheet_sheet_sheet s
                                    LEFT JOIN resource_resource r
                                        LEFT JOIN hr_employee e
                                        ON (e.resource_id = r.id)
                                    ON (s.user_id = r.user_id))
                                ON (a.employee_id = e.id
                                    AND s.date_to >= date_trunc('day',a.name)
                                    AND s.date_from <= a.name)
                            WHERE action in ('sign_in', 'sign_out')
                            group by a.name::date, s.id
                        )) AS foo
                        GROUP BY name, sheet_id
                )) AS bar""")

hr_timesheet_sheet_sheet_day()


class hr_timesheet_sheet_sheet_account(osv.osv):
    _name = "hr_timesheet_sheet.sheet.account"
    _description = "Timesheets by Period"
    _auto = False
    _order='name'
    _columns = {
        'name': fields.many2one('account.analytic.account', 'Project / Analytic Account', readonly=True),
        'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True),
        'total': fields.float('Total Time', digits=(16,2), readonly=True),
        'invoice_rate': fields.many2one('hr_timesheet_invoice.factor', 'Invoice rate', readonly=True),
        }

    def init(self, cr):
        cr.execute("""create or replace view hr_timesheet_sheet_sheet_account as (
            select
                min(hrt.id) as id,
                l.account_id as name,
                s.id as sheet_id,
                sum(l.unit_amount) as total,
                l.to_invoice as invoice_rate
            from
                hr_analytic_timesheet hrt
                left join (account_analytic_line l
                    LEFT JOIN hr_timesheet_sheet_sheet s
                        ON (s.date_to >= l.date
                            AND s.date_from <= l.date
                            AND s.user_id = l.user_id))
                    on (l.id = hrt.line_id)
            group by l.account_id, s.id, l.to_invoice
        )""")

hr_timesheet_sheet_sheet_account()



class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'timesheet_range': fields.selection(
            [('day','Day'),('week','Week'),('month','Month')], 'Timesheet range',
            help="Periodicity on which you validate your timesheets."),
        'timesheet_max_difference': fields.float('Timesheet allowed difference(Hours)',
            help="Allowed difference in hours between the sign in/out and the timesheet " \
                 "computation for one sheet. Set this to 0 if you do not want any control."),
    }
    _defaults = {
        'timesheet_range': lambda *args: 'week',
        'timesheet_max_difference': lambda *args: 0.0
    }

res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

