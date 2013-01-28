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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc

class hr_timesheet_sheet(osv.osv):
    _name = "hr_timesheet_sheet.sheet"
    _inherit = "mail.thread"
    _table = 'hr_timesheet_sheet_sheet'
    _order = "id desc"
    _description="Timesheet"

    def _total(self, cr, uid, ids, name, args, context=None):
        """ Compute the attendances, analytic lines timesheets and differences between them
            for all the days of a timesheet and the current day
        """

        res = {}
        for sheet in self.browse(cr, uid, ids, context=context or {}):
            res.setdefault(sheet.id, {
                'total_attendance': 0.0,
                'total_timesheet': 0.0,
                'total_difference': 0.0,
            })
            for period in sheet.period_ids:
                res[sheet.id]['total_attendance'] += period.total_attendance
                res[sheet.id]['total_timesheet'] += period.total_timesheet
                res[sheet.id]['total_difference'] += period.total_attendance - period.total_timesheet
        return res

    def check_employee_attendance_state(self, cr, uid, sheet_id, context=None):
        ids_signin = self.pool.get('hr.attendance').search(cr,uid,[('sheet_id', '=', sheet_id),('action','=','sign_in')])
        ids_signout = self.pool.get('hr.attendance').search(cr,uid,[('sheet_id', '=', sheet_id),('action','=','sign_out')])

        if len(ids_signin) != len(ids_signout):
            raise osv.except_osv(('Warning!'),_('The timesheet cannot be validated as it does not contain an equal number of sign ins and sign outs.'))
        return True

    def copy(self, cr, uid, ids, *args, **argv):
        raise osv.except_osv(_('Error!'), _('You cannot duplicate a timesheet.'))

    def create(self, cr, uid, vals, *args, **argv):
        if 'employee_id' in vals:
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).user_id:
                raise osv.except_osv(_('Error!'), _('In order to create a timesheet for this employee, you must assign it to a user.'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).product_id:
                raise osv.except_osv(_('Error!'), _('In order to create a timesheet for this employee, you must link the employee to a product, like \'Consultant\'.'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).journal_id:
                raise osv.except_osv(_('Configuration Error!'), _('In order to create a timesheet for this employee, you must assign an analytic journal to the employee, like \'Timesheet Journal\'.'))
        return super(hr_timesheet_sheet, self).create(cr, uid, vals, *args, **argv)

    def write(self, cr, uid, ids, vals, *args, **argv):
        if 'employee_id' in vals:
            new_user_id = self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).user_id.id or False
            if not new_user_id:
                raise osv.except_osv(_('Error!'), _('In order to create a timesheet for this employee, you must assign it to a user.'))
            if not self._sheet_date(cr, uid, ids, forced_user_id=new_user_id):
                raise osv.except_osv(_('Error!'), _('You cannot have 2 timesheets that overlap!\nYou should use the menu \'My Timesheet\' to avoid this problem.'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).product_id:
                raise osv.except_osv(_('Error!'), _('In order to create a timesheet for this employee, you must link the employee to a product.'))
            if not self.pool.get('hr.employee').browse(cr, uid, vals['employee_id']).journal_id:
                raise osv.except_osv(_('Configuration Error!'), _('In order to create a timesheet for this employee, you must assign an analytic journal to the employee, like \'Timesheet Journal\'.'))
        return super(hr_timesheet_sheet, self).write(cr, uid, ids, vals, *args, **argv)

    def button_confirm(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context):
            if sheet.employee_id and sheet.employee_id.parent_id and sheet.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [sheet.id], user_ids=[sheet.employee_id.parent_id.user_id.id], context=context)
            self.check_employee_attendance_state(cr, uid, sheet.id, context=context)
            di = sheet.user_id.company_id.timesheet_max_difference
            if (abs(sheet.total_difference) < di) or not di:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'hr_timesheet_sheet.sheet', sheet.id, 'confirm', cr)
            else:
                raise osv.except_osv(_('Warning!'), _('Please verify that the total difference of the sheet is lower than %.2f.') %(di,))
        return True

    def attendance_action_change(self, cr, uid, ids, context=None):
        hr_employee = self.pool.get('hr.employee')
        employee_ids = []
        for sheet in self.browse(cr, uid, ids, context=context):
            if sheet.employee_id.id not in employee_ids: employee_ids.append(sheet.employee_id.id)
        return hr_employee.attendance_action_change(cr, uid, employee_ids, context=context)

    _columns = {
        'name': fields.char('Note', size=64, select=1,
                            states={'confirm':[('readonly', True)], 'done':[('readonly', True)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'user_id': fields.related('employee_id', 'user_id', type="many2one", relation="res.users", store=True, string="User", required=False, readonly=True),#fields.many2one('res.users', 'User', required=True, select=1, states={'confirm':[('readonly', True)], 'done':[('readonly', True)]}),
        'date_from': fields.date('Date from', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}),
        'date_to': fields.date('Date to', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}),
        'timesheet_ids' : fields.one2many('hr.analytic.timesheet', 'sheet_id',
            'Timesheet lines',
            readonly=True, states={
                'draft': [('readonly', False)],
                'new': [('readonly', False)]}
            ),
        'attendances_ids' : fields.one2many('hr.attendance', 'sheet_id', 'Attendances'),
        'state' : fields.selection([
            ('new', 'New'),
            ('draft','Open'),
            ('confirm','Waiting Approval'),
            ('done','Approved')], 'Status', select=True, required=True, readonly=True,
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed timesheet. \
                \n* The \'Confirmed\' status is used for to confirm the timesheet by user. \
                \n* The \'Done\' status is used when users timesheet is accepted by his/her senior.'),
        'state_attendance' : fields.related('employee_id', 'state', type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Current Status', readonly=True),
        'total_attendance': fields.function(_total, method=True, string='Total Attendance', multi="_total"),
        'total_timesheet': fields.function(_total, method=True, string='Total Timesheet', multi="_total"),
        'total_difference': fields.function(_total, method=True, string='Difference', multi="_total"),
        'period_ids': fields.one2many('hr_timesheet_sheet.sheet.day', 'sheet_id', 'Period', readonly=True),
        'account_ids': fields.one2many('hr_timesheet_sheet.sheet.account', 'sheet_id', 'Analytic accounts', readonly=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'department_id':fields.many2one('hr.department','Department'),
    }

    def _default_date_from(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r=='month':
            return time.strftime('%Y-%m-01')
        elif r=='week':
            return (datetime.today() + relativedelta(weekday=0, days=-6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-01-01')
        return time.strftime('%Y-%m-%d')

    def _default_date_to(self, cr, uid, context=None):
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


    _constraints = [
        (_sheet_date, 'You cannot have 2 timesheets that overlap!\nPlease use the menu \'My Current Timesheet\' to avoid this problem.', ['date_from','date_to']),
    ]

    def action_set_to_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'draft'})
        wf_service = netsvc.LocalService('workflow')
        for id in ids:
            wf_service.trg_create(uid, self._name, id, cr)
        return True

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        return [(r['id'], _('Week ')+datetime.strptime(r['date_from'], '%Y-%m-%d').strftime('%U')) \
                for r in self.read(cr, uid, ids, ['date_from'],
                    context=context, load='_classic_write')]

    def unlink(self, cr, uid, ids, context=None):
        sheets = self.read(cr, uid, ids, ['state','total_attendance'], context=context)
        for sheet in sheets:
            if sheet['state'] in ('confirm', 'done'):
                raise osv.except_osv(_('Invalid Action!'), _('You cannot delete a timesheet which is already confirmed.'))
            elif sheet['total_attendance'] <> 0.00:
                raise osv.except_osv(_('Invalid Action!'), _('You cannot delete a timesheet which have attendance entries.'))
        return super(hr_timesheet_sheet, self).unlink(cr, uid, ids, context=context)

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        department_id =  False
        if employee_id:
            empl_id = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
            department_id = empl_id.department_id.id
            user_id = empl_id.user_id.id
        return {'value': {'department_id': department_id, 'user_id': user_id,}}

    # ------------------------------------------------
    # OpenChatter methods and notifications
    # ------------------------------------------------

    def _needaction_domain_get(self, cr, uid, context=None):
        emp_obj = self.pool.get('hr.employee')
        empids = emp_obj.search(cr, uid, [('parent_id.user_id', '=', uid)], context=context)
        if not empids:
            return False
        dom = ['&', ('state', '=', 'confirm'), ('employee_id', 'in', empids)]
        return dom


class account_analytic_line(osv.osv):
    _inherit = "account.analytic.line"

    def _get_default_date(self, cr, uid, context=None):
        if context is None:
            context = {}
        #get the default date (should be: today)
        res = super(account_analytic_line, self)._get_default_date(cr, uid, context=context)
        #if we got the dates from and to from the timesheet and if the default date is in between, we use the default
        #but if the default isn't included in those dates, we use the date start of the timesheet as default
        if context.get('timesheet_date_from') and context.get('timesheet_date_to'):
            if context['timesheet_date_from'] <= res <= context['timesheet_date_to']:
                return res
            return context.get('timesheet_date_from')
        #if we don't get the dates from the timesheet, we return the default value from super()
        return res


class hr_timesheet_line(osv.osv):
    _inherit = "hr.analytic.timesheet"

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
            type='many2one', relation='hr_timesheet_sheet.sheet', ondelete="cascade",
            store={
                    'hr_timesheet_sheet.sheet': (_get_hr_timesheet_sheet, ['employee_id', 'date_from', 'date_to'], 10),
                    'account.analytic.line': (_get_account_analytic_line, ['user_id', 'date'], 10),
                    'hr.analytic.timesheet': (lambda self,cr,uid,ids,context=None: ids, None, 10),
                  },
            ),
    }

    def _check_sheet_state(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for timesheet_line in self.browse(cr, uid, ids, context=context):
            if timesheet_line.sheet_id and timesheet_line.sheet_id.state not in ('draft', 'new'):
                return False
        return True

    _constraints = [
        (_check_sheet_state, 'You cannot modify an entry in a Confirmed/Done timesheet !', ['state']),
    ]

    def unlink(self, cr, uid, ids, *args, **kwargs):
        if isinstance(ids, (int, long)):
            ids = [ids]
        self._check(cr, uid, ids)
        return super(hr_timesheet_line,self).unlink(cr, uid, ids,*args, **kwargs)

    def _check(self, cr, uid, ids):
        for att in self.browse(cr, uid, ids):
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error!'), _('You cannot modify an entry in a confirmed timesheet.'))
        return True

    def multi_on_change_account_id(self, cr, uid, ids, account_ids, context=None):
        return dict([(el, self.on_change_account_id(cr, uid, ids, el, context.get('user_id', uid))) for el in account_ids])


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
                raise osv.except_osv(_('Error!'), _('You cannot modify an entry in a confirmed timesheet.'))
        res = super(hr_attendance,self).create(cr, uid, vals, context=context)
        if 'sheet_id' in context:
            if context['sheet_id'] != self.browse(cr, uid, res, context=context).sheet_id.id:
                raise osv.except_osv(_('User Error!'), _('You cannot enter an attendance ' \
                        'date outside the current timesheet dates.'))
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
                    raise osv.except_osv(_('User Error!'), _('You cannot enter an attendance ' \
                            'date outside the current timesheet dates.'))
        return res

    def _check(self, cr, uid, ids):
        for att in self.browse(cr, uid, ids):
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise osv.except_osv(_('Error!'), _('You cannot modify an entry in a confirmed timesheet'))
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

