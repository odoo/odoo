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
from datetime import datetime
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

        # dict:
        # {idn: (date_current, user_id), ...
        #  1: ('2010-08-15', 1)}
        res6 = dict([(rec['id'], (rec['date_current'], rec['user_id'][0]))
                        for rec
                            in obj.read(cr, user, ids, ['date_current', 'user_id'], context=context)])

        # eg: ['|', '|',
        #       '&', '&', ('name', '>=', '2011-03-01'), ('name', '<=', '2011-03-01'), ('employee_id.user_id', '=', 1),
        #       '&', '&', ('name', '>=', '2011-02-01'), ('name', '<=', '2011-02-01'), ('employee_id.user_id', '=', 1)]
        dom = []
        for c, id in enumerate(ids):
            if id in res6:
                if c: # skip first
                    dom.insert(0 ,'|')
                dom.append('&')
                dom.append('&')
                dom.append(('name', '>=', res6[id][0]))
                dom.append(('name', '<=', res6[id][0]))
                dom.append(('employee_id.user_id', '=', res6[id][1]))

        ids2 = obj.pool.get(self._obj).search(cr, user, dom, limit=self._limit)

        res = {}
        for i in ids:
            res[i] = []

        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
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


        res5 = obj.read(cr, user, ids, ['date_current', 'user_id'], context=context)
        res6 = {}
        for r in res5:
            res6[r['id']] = (r['date_current'], r['user_id'][0])

        ids2 = []
        for id in ids:
            dom = []
            if id in res6:
                dom = [('date', '=', res6[id][0]), ('user_id', '=', res6[id][1])]
            ids2.extend(obj.pool.get(self._obj).search(cr, user,
                dom, limit=self._limit))
        res = {}
        for i in ids:
            res[i] = []
        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2,
                [self._fields_id], context=context, load='_classic_write'):
            if r[self._fields_id]:
                res[r[self._fields_id][0]].append(r['id'])

        return res

class hr_timesheet_sheet(osv.osv):
    _name = "hr_timesheet_sheet.sheet"
    _table = 'hr_timesheet_sheet_sheet'
    _order = "id desc"
    _description="Timesheet"

    def _total_day(self, cr, uid, ids, name, args, context=None):
        res = {}
        cr.execute('SELECT sheet.id, day.total_attendance, day.total_timesheet, day.total_difference\
                FROM hr_timesheet_sheet_sheet AS sheet \
                LEFT JOIN hr_timesheet_sheet_sheet_day AS day \
                    ON (sheet.id = day.sheet_id \
                        AND day.name = sheet.date_current) \
                WHERE sheet.id IN %s',(tuple(ids),))
        for record in cr.fetchall():
            res[record[0]] = {}
            res[record[0]]['total_attendance_day'] = record[1]
            res[record[0]]['total_timesheet_day'] = record[2]
            res[record[0]]['total_difference_day'] = record[3]
        return res

    def _total(self, cr, uid, ids, name, args, context=None):
        res = {}
        cr.execute('SELECT s.id, COALESCE(SUM(d.total_attendance),0), COALESCE(SUM(d.total_timesheet),0), COALESCE(SUM(d.total_difference),0) \
                FROM hr_timesheet_sheet_sheet s \
                    LEFT JOIN hr_timesheet_sheet_sheet_day d \
                        ON (s.id = d.sheet_id) \
                WHERE s.id IN %s GROUP BY s.id',(tuple(ids),))
        for record in cr.fetchall():
            res[record[0]] = {}
            res[record[0]]['total_attendance'] = record[1]
            res[record[0]]['total_timesheet'] = record[2]
            res[record[0]]['total_difference'] = record[3]
        return res

    def _state_attendance(self, cr, uid, ids, name, args, context=None):
        emp_obj = self.pool.get('hr.employee')
        result = {}
        link_emp = {}
        emp_ids = []

        for sheet in self.browse(cr, uid, ids, context=context):
            result[sheet.id] = 'none'
            emp_ids2 = emp_obj.search(cr, uid,
                    [('user_id', '=', sheet.user_id.id)], context=context)
            if emp_ids2:
                link_emp[emp_ids2[0]] = sheet.id
                emp_ids.append(emp_ids2[0])
        for emp in emp_obj.browse(cr, uid, emp_ids, context=context):
            if emp.id in link_emp:
                sheet_id = link_emp[emp.id]
                result[sheet_id] = emp.state
        return result

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
            self.check_employee_attendance_state(cr, uid, sheet.id, context)
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

    def sign(self, cr, uid, ids, typ, context=None):
        emp_obj = self.pool.get('hr.employee')
        sheet = self.browse(cr, uid, ids, context=context)[0]
        if context is None:
            context = {}
        if not sheet.date_current == time.strftime('%Y-%m-%d'):
            raise osv.except_osv(_('Error !'), _('You cannot sign in/sign out from an other date than today'))
        emp_id = sheet.employee_id.id
        context['sheet_id']=ids[0]
        emp_obj.attendance_action_change(cr, uid, [emp_id], type=typ, context=context,)
        return True

    def sign_in(self, cr, uid, ids, context=None):
        return self.sign(cr,uid,ids,'sign_in',context=None)

    def sign_out(self, cr, uid, ids, context=None):
        return self.sign(cr,uid,ids,'sign_out',context=None)

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
            ('done','Approved')], 'State', select=True, required=True, readonly=True,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed timesheet. \
                \n* The \'Confirmed\' state is used for to confirm the timesheet by user. \
                \n* The \'Done\' state is used when users timesheet is accepted by his/her senior.'),
        'state_attendance' : fields.function(_state_attendance, type='selection', selection=[('absent', 'Absent'), ('present', 'Present'),('none','No employee defined')], string='Current Status'),
        'total_attendance_day': fields.function(_total_day, string='Total Attendance', multi="_total_day"),
        'total_timesheet_day': fields.function(_total_day, string='Total Timesheet', multi="_total_day"),
        'total_difference_day': fields.function(_total_day, string='Difference', multi="_total_day"),
        'total_attendance': fields.function(_total, string='Total Attendance', multi="_total_sheet"),
        'total_timesheet': fields.function(_total, string='Total Timesheet', multi="_total_sheet"),
        'total_difference': fields.function(_total, string='Difference', multi="_total_sheet"),
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
            return (datetime.today() + relativedelta(weekday=0, weeks=-1)).strftime('%Y-%m-%d')
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
                    WHERE (date_from < %s and %s < date_to) \
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
        cursor.execute('SELECT l.id, COALESCE(MAX(s.id), 0) \
                FROM hr_timesheet_sheet_sheet s \
                    LEFT JOIN (hr_analytic_timesheet l \
                        LEFT JOIN account_analytic_line al \
                            ON (l.line_id = al.id)) \
                        ON (s.date_to >= al.date \
                            AND s.date_from <= al.date \
                            AND s.user_id = al.user_id) \
                WHERE l.id IN %s GROUP BY l.id',(tuple(ids),))
        res = dict(cursor.fetchall())
        sheet_names = {}
        for sheet_id, name in sheet_obj.name_get(cursor, user, res.values(),
                context=context):
            sheet_names[sheet_id] = name

        for line_id in {}.fromkeys(ids):
            sheet_id = res.get(line_id, False)
            if sheet_id:
                res[line_id] = (sheet_id, sheet_names[sheet_id])
            else:
                res[line_id] = False
        return res

    def _sheet_search(self, cursor, user, obj, name, args, context=None):
        if not len(args):
            return []
        sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')

        i = 0
        while i < len(args):
            fargs = args[i][0].split('.', 1)
            if len(fargs) > 1:
                args[i] = (fargs[0], 'in', sheet_obj.search(cursor, user,
                    [(fargs[1], args[i][1], args[i][2])], context=context))
                i += 1
                continue
            if isinstance(args[i][2], basestring):
                res_ids = sheet_obj.name_search(cursor, user, args[i][2], [],
                        args[i][1])
                args[i] = (args[i][0], 'in', [x[0] for x in res_ids])
            i += 1
        qu1, qu2 = [], []
        for x in args:
            if x[1] != 'in':
                if (x[2] is False) and (x[1] == '='):
                    qu1.append('(s.id IS NULL)')
                elif (x[2] is False) and (x[1] == '<>' or x[1] == '!='):
                    qu1.append('(s.id IS NOT NULL)')
                else:
                    qu1.append('(s.id %s %s)' % (x[1], '%s'))
                    qu2.append(x[2])
            elif x[1] == 'in':
                if len(x[2]) > 0:
                    qu1.append('(s.id in (%s))' % (','.join(['%d'] * len(x[2]))))
                    qu2 += x[2]
                else:
                    qu1.append('(False)')
        if len(qu1):
            qu1 = ' WHERE ' + ' AND '.join(qu1)
        else:
            qu1 = ''
        cursor.execute('SELECT l.id \
                FROM hr_timesheet_sheet_sheet s \
                    LEFT JOIN (hr_analytic_timesheet l \
                        LEFT JOIN account_analytic_line al \
                            ON (l.line_id = al.id)) \
                        ON (s.date_to >= al.date \
                            AND s.date_from <= al.date \
                            AND s.user_id = al.user_id)' + \
                qu1, qu2)
        res = cursor.fetchall()
        if not len(res):
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    _columns = {
        'sheet_id': fields.function(_sheet, string='Sheet',
            type='many2one', relation='hr_timesheet_sheet.sheet',
            fnct_search=_sheet_search),
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

    def _sheet(self, cursor, user, ids, name, args, context=None):
        sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
        cursor.execute("SELECT a.id, COALESCE(MAX(s.id), 0) \
                FROM hr_timesheet_sheet_sheet s \
                    LEFT JOIN (hr_attendance a \
                        LEFT JOIN hr_employee e \
                            LEFT JOIN resource_resource r \
                                ON (e.resource_id = r.id) \
                            ON (a.employee_id = e.id)) \
                        ON (s.date_to >= date_trunc('day',a.name) \
                            AND s.date_from <= a.name \
                            AND s.user_id = r.user_id) \
                WHERE a.id IN %s GROUP BY a.id",(tuple(ids),))
        res = dict(cursor.fetchall())
        sheet_names = {}
        for sheet_id, name in sheet_obj.name_get(cursor, user, res.values(),
                context=context):
            sheet_names[sheet_id] = name
        for line_id in {}.fromkeys(ids):
            sheet_id = res.get(line_id, False)
            if sheet_id:
                res[line_id] = (sheet_id, sheet_names[sheet_id])
            else:
                res[line_id] = False
        return res

    def _sheet_search(self, cursor, user, obj, name, args, context=None):
        if not len(args):
            return []

        sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
        i = 0
        while i < len(args):
            fargs = args[i][0].split('.', 1)
            if len(fargs) > 1:
                args[i] = (fargs[0], 'in', sheet_obj.search(cursor, user,
                    [(fargs[1], args[i][1], args[i][2])], context=context))
                i += 1
                continue
            if isinstance(args[i][2], basestring):
                res_ids = sheet_obj.name_search(cursor, user, args[i][2], [],
                        args[i][1])
                args[i] = (args[i][0], 'in', [x[0] for x in res_ids])
            i += 1
        qu1, qu2 = [], []
        for x in args:
            if x[1] != 'in':
                if (x[2] is False) and (x[1] == '='):
                    qu1.append('(s.id IS NULL)')
                elif (x[2] is False) and (x[1] == '<>' or x[1] == '!='):
                    qu1.append('(s.id IS NOT NULL)')
                else:
                    qu1.append('(s.id %s %s)' % (x[1], '%s'))
                    qu2.append(x[2])
            elif x[1] == 'in':
                if len(x[2]) > 0:
                    qu1.append('(s.id in (%s))' % (','.join(['%d'] * len(x[2]))))
                    qu2 += x[2]
                else:
                    qu1.append('(False)')
        if len(qu1):
            qu1 = ' WHERE ' + ' AND '.join(qu1)
        else:
            qu1 = ''
        cursor.execute('SELECT a.id\
                FROM hr_timesheet_sheet_sheet s \
                    LEFT JOIN (hr_attendance a \
                        LEFT JOIN hr_employee e \
                            ON (a.employee_id = e.id)) \
                                LEFT JOIN resource_resource r \
                                    ON (e.resource_id = r.id) \
                        ON (s.date_to >= date_trunc(\'day\',a.name) \
                            AND s.date_from <= a.name \
                            AND s.user_id = r.user_id) ' + \
                qu1, qu2)
        res = cursor.fetchall()
        if not len(res):
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    _columns = {
        'sheet_id': fields.function(_sheet, string='Sheet',
            type='many2one', relation='hr_timesheet_sheet.sheet',
            fnct_search=_sheet_search),
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
                raise osv.except_osv(_('Error !'), _('You cannot modify an entry in a confirmed timesheet!'))
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

