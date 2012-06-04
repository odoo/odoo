# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
import tools


class one2many_mod3(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        res = {}
        for obj in obj.browse(cr, user, ids, context=context):
            res[obj.id] = []
            list_ids = []
            children = obj.pool.get('report_account_analytic.planning')._child_compute(cr, user, [obj.user_id.id], '', [])
            for u_id in children.get(obj.user_id.id, []):
                list_ids.append(u_id)
            list_ids.append(obj.user_id.id)
            ids2 = obj.pool.get(self._obj).search(cr, user, ['&',(self._fields_id,'=',obj.id),'|',('user_id','in',list_ids),('user_id','=',False)], limit=self._limit)
            for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
                if r[self._fields_id] not in res:
                    res[r[self._fields_id]] = []
                res[r[self._fields_id]].append( r['id'] )
        return res

class report_account_analytic_planning(osv.osv):
    _name = "report_account_analytic.planning"
    _description = "Planning"

    def emp_to_users(self, cr, uid, ids, context=None):
        employees = self.pool.get('hr.employee').browse(cr, uid, ids, context=context)
        user_ids = [e.user_id.id for e in employees if e.user_id]
        return user_ids

    def _child_compute(self, cr, uid, ids, name, args, context=None):
        obj_dept = self.pool.get('hr.department')
        obj_user = self.pool.get('res.users')
        result = {}
        for user_id in ids:
            child_ids = []
            cr.execute("""SELECT dept.id FROM hr_department AS dept
                LEFT JOIN hr_employee AS emp ON dept.manager_id = emp.id
                WHERE emp.id IN
                    (SELECT emp.id FROM hr_employee
                        JOIN resource_resource r ON r.id = emp.resource_id WHERE r.user_id = %s)
                """, (user_id,))
            mgnt_dept_ids = [x[0] for x in cr.fetchall()]
            ids_dept = obj_dept.search(cr, uid, [('id', 'child_of', mgnt_dept_ids)], context=context)
            if ids_dept:
                data_dept = obj_dept.read(cr, uid, ids_dept, ['member_ids'], context=context)
                emp_children = map(lambda x: x['member_ids'], data_dept)
                emp_children = tools.flatten(emp_children)
                children = self.emp_to_users(cr, uid, emp_children, context=context)
                children = obj_user.search(cr, uid, [('id', 'in', children),('active', '=', True)], context=context)
                if user_id in children:
                    children.remove(user_id)
                child_ids = list(set(child_ids + children))
            result[user_id] = child_ids
        return result

    def _get_total_planned(self, cr, uid, ids, name, args, context=None):
        result = {}
        for plan in self.browse(cr, uid, ids, context=context):
            plan_hrs=0.0
            for p in plan.planning_user_ids:
                if not p.plan_open : p.plan_open = 0.0
                if not p.plan_tasks : p.plan_tasks = 0.0
                plan_hrs = plan_hrs + p.plan_open + p.plan_tasks
            result[plan.id] = plan_hrs
        return result

    def _get_total_free(self, cr, uid, ids, name, args, context=None):
        result = {}
        for plan in self.browse(cr, uid, ids, context=context):
            total_free = 0.0
            for p in plan.planning_user_ids:
                if  p.free:
                    total_free = total_free + p.free
            result[plan.id] = total_free
        return result

    def _check_planning_responsible(self, cr, uid, ids, context=None):
        for obj_plan in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                SELECT id FROM report_account_analytic_planning plan
                WHERE (   (%(date_from)s BETWEEN date_from AND date_to)
                                OR (%(date_to)s BETWEEN date_from AND date_to)
                                OR (%(date_from)s < date_from AND %(date_to)s > date_to)
                               )  AND user_id = %(uid)s AND id <> %(id)s""",
                        {"date_from": obj_plan.date_from,
                         "date_to": obj_plan.date_to,
                         "uid": obj_plan.user_id.id,
                         "id" : obj_plan.id}
                               )

            res = cr.fetchone()
            if res:
                return False
        return True

    _columns = {
        'name': fields.char('Planning Name', required=True, size=32, states={'done':[('readonly', True)]}),
        'code': fields.char('Code', size=32, states={'done':[('readonly', True)]}),
        'user_id': fields.many2one('res.users', 'Responsible', required=True, states={'done':[('readonly', True)]}),
        'date_from': fields.date('Start Date', required=True, states={'done':[('readonly', True)]}),
        'date_to':fields.date('End Date', required=True, states={'done':[('readonly', True)]}),
        'line_ids': fields.one2many('report_account_analytic.planning.line', 'planning_id', 'Planning lines', states={'done':[('readonly', True)]}),
        'stat_ids': fields.one2many('report_account_analytic.planning.stat', 'planning_id', 'Planning analysis', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('cancel', 'Cancelled'), ('open', 'Open'), ('done', 'Done')], 'Status', required=True),
        'business_days': fields.integer('Business Days', required=True, states={'done':[('readonly', True)]}, help='Set here the number of working days within this planning for one person full time'),
        'planning_user_ids': one2many_mod3('report_account_analytic.planning.user', 'planning_id', 'Planning By User'),
        'planning_account': fields.one2many('report_account_analytic.planning.account', 'planning_id', 'Planning By Account'),
        'total_planned': fields.function(_get_total_planned, string='Total Planned'),
        'total_free': fields.function(_get_total_free, string='Total Free'),
    }
    _defaults = {
        'date_from': lambda self,cr,uid,ctx: fields.date.context_today(self,cr,uid,timestamp=(datetime.now()+relativedelta(day=1)),context=ctx),
        'date_to': lambda self,cr,uid,ctx: fields.date.context_today(self,cr,uid,timestamp=(datetime.now()+relativedelta(months=1, day=1, days=-1)),context=ctx),
        'user_id': lambda self, cr, uid, c: uid,
        'state': 'draft',
        'business_days': 20,
    }
    _order = 'date_from desc'

    _constraints = [
        (_check_planning_responsible, 'Invalid planning ! Planning dates can\'t overlap for the same responsible. ', ['user_id'])
    ]

    def action_open(self, cr, uid, id, context=None):
        self.write(cr, uid, id, {'state' : 'open'}, context=context)
        return True

    def action_cancel(self, cr, uid, id, context=None):
        self.write(cr, uid, id, {'state' : 'cancel'}, context=context)
        return True

    def action_draft(self, cr, uid, id, context=None):
        self.write(cr, uid, id, {'state' : 'draft'}, context=context)
        return True

    def action_done(self, cr, uid, id, context=None):
        self.write(cr, uid, id, {'state' : 'done'}, context=context)
        return True

report_account_analytic_planning()

class report_account_analytic_planning_line(osv.osv):
    _name = "report_account_analytic.planning.line"
    _description = "Planning Line"
    _rec_name = 'user_id'

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['user_id', 'planning_id', 'note'], context=context)
        res = []
        for record in reads:
            name = '['+record['planning_id'][1]
            if record['user_id']:
                name += " - " +record['user_id'][1]+'] '
            else:
                name += '] '
            if record['note']:
                name += record['note']
            res.append((record['id'], name))
        return res

    def _amount_base_uom(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm and tm.factor:
            div = tm.factor
        else:
            div = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = line.amount / line.amount_unit.factor * div
        return result

    _columns = {
        'account_id': fields.many2one('account.analytic.account', 'Analytic account', select=True),
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning', required=True, ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'User', select=True),
        'amount': fields.float('Quantity', required=True),
        'amount_unit': fields.many2one('product.uom', 'Qty Unit of Measure', required=True),
        'note': fields.text('Note', size=64),
        'amount_in_base_uom': fields.function(_amount_base_uom, string='Quantity in base Unit of Measure', store=True),
        'task_ids': fields.one2many('project.task', 'planning_line_id', 'Planning Tasks'),
    }
    _order = 'user_id, account_id'

report_account_analytic_planning_line()

class account_analytic_account(osv.osv):
    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'
    _columns = {
        'planning_ids': fields.one2many('report_account_analytic.planning.line', 'account_id', 'Plannings'),
    }

account_analytic_account()

class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'planning_line_id': fields.many2one('report_account_analytic.planning.line', 'Planning', ondelete='cascade'),
    }

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if not context.get('planning', False):
            return super(project_task,self).search(cr, user, args,
                offset=offset, limit=limit, order=order, context=context, count=count)
        cr.execute(" SELECT t.id, t.name \
                        from project_task t \
                        join report_account_analytic_planning_line l on (l.id = t.planning_line_id )\
                        where l.planning_id=%s",(context.get('planning'),))
        ids = map(lambda x: x[0], cr.fetchall())
        return ids

project_task()

class report_account_analytic_planning_user(osv.osv):
    _name = "report_account_analytic.planning.user"
    _description = "Planning by User"
    _rec_name = 'user_id'
    _auto = False

    def _get_tasks(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm = users_obj.browse(cr, uid, uid, context=context).company_id.project_time_mode_id
        if tm and tm.factor:
            div = tm.factor
        else:
            div = 1.0
        tm2 = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm2 and tm2.factor:
            div2 = tm2.factor
        else:
            div2 = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            if line.user_id:
                cr.execute("""select COALESCE(sum(tasks.remaining_hours),0) from project_task tasks \
                               where  tasks.planning_line_id IN (select id from report_account_analytic_planning_line\
                where planning_id = %s and user_id=%s)""", (line.planning_id.id, line.user_id.id,))

                result[line.id] = cr.fetchall()[0][0] / div * div2
            else:
                result[line.id] = 0
        return result

    def _get_free(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.user_id:
                result[line.id] = line.planning_id.business_days - line.plan_tasks - line.plan_open - line.holiday
            else:
                result[line.id] = 0.0
        return result

    def _get_timesheets(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm2 = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm2 and tm2.factor:
            div2 = tm2.factor
        else:
            div2 = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            if line.user_id:
                cr.execute("""
                SELECT sum(unit_amount/uom.factor) FROM account_analytic_line acc
                LEFT JOIN product_uom uom ON (uom.id = acc.product_uom_id)
                WHERE acc.date>=%s and acc.date<=%s and acc.user_id=%s""", (line.planning_id.date_from, line.planning_id.date_to, line.user_id.id ))
                res = cr.fetchall()
                result[line.id] = res[0][0] and res[0][0] * div2 or False
            else:
                result[line.id] = 0
        return result

    _columns = {
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning'),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'tasks': fields.function(_get_tasks, string='Remaining Tasks', help='This value is given by the sum of work remaining to do on the task for this planning, expressed in days.'),
        'plan_tasks': fields.float('Time Planned on Tasks', readonly=True, help='This value is given by the sum of time allocation with task(s) linked, expressed in days.'),
        'free': fields.function(_get_free, string='Unallocated Time', readonly=True, help='Computed as \
Business Days - (Time Allocation of Tasks + Time Allocation without Tasks + Holiday Leaves)'),
        'plan_open': fields.float('Time Allocation without Tasks', readonly=True,help='This value is given by the sum of time allocation without task(s) linked, expressed in days.'),
        'holiday': fields.float('Leaves',help='This value is given by the total of validated leaves into the \'Date From\' and \'Date To\' of the planning.'),
        'timesheet': fields.function(_get_timesheets, string='Timesheet', help='This value is given by the sum of all work encoded in the timesheet(s) between the \'Date From\' and \'Date To\' of the planning.'),
    }

    def init(self, cr):
        cr.execute(""" CREATE OR REPLACE VIEW report_account_analytic_planning_user AS (
        SELECT
            planning.id AS planning_id,
            (1000*(planning.id) + users.id)::integer AS id,
            planning.business_days,
            users.id AS user_id,
            (SELECT sum(line1.amount_in_base_uom)
                FROM report_account_analytic_planning_line line1
                WHERE   (
                        SELECT COUNT(1)
                        FROM project_task task
                        WHERE task.planning_line_id = line1.id
                        ) > 0
                AND line1.user_id = users.id
                AND line1.planning_id = planning.id
            )AS plan_tasks,
            (SELECT SUM(line1.amount_in_base_uom)
                FROM report_account_analytic_planning_line line1
                WHERE   (
                        SELECT COUNT(1)
                        FROM project_task task
                        WHERE task.planning_line_id = line1.id
                        ) = 0
                AND line1.user_id = users.id
                AND line1.planning_id = planning.id
            ) AS plan_open,
            (SELECT -(SUM(holidays.number_of_days))
                FROM hr_holidays holidays
                WHERE holidays.employee_id IN
                    (
                    SELECT emp.id
                    FROM hr_employee emp, resource_resource res WHERE emp.resource_id = res.id and res.user_id = users.id
                    )
                AND holidays.state IN ('validate')
                AND holidays.type = 'remove'
                AND holidays.date_from >= planning.date_from
                AND holidays.date_to <= planning.date_to
            ) AS holiday

        FROM report_account_analytic_planning planning
        LEFT JOIN report_account_analytic_planning_line line ON (line.planning_id = planning.id), res_users users
        GROUP BY planning.id, planning.business_days, users.id, planning.date_from, planning.date_to

        UNION

        SELECT
            planning.id AS planning_id,
            (1000*(planning.id) - 1)::integer AS id,
            planning.business_days,
            line.user_id,
            (SELECT SUM(line1.amount_in_base_uom)
                FROM report_account_analytic_planning_line line1
                WHERE (SELECT COUNT(1) FROM project_task task WHERE task.planning_line_id = line1.id) > 0
                AND line1.user_id IS NULL
            ) AS plan_tasks,
            (SELECT SUM(line1.amount_in_base_uom)
                FROM report_account_analytic_planning_line line1
                WHERE (SELECT COUNT(1) FROM project_task task WHERE task.planning_line_id = line1.id) = 0
                AND line1.user_id IS NULL
            ) AS plan_open,
            '0' AS holiday
        FROM report_account_analytic_planning planning
        INNER JOIN report_account_analytic_planning_line line ON line.planning_id = planning.id
            AND line.user_id IS NULL
        GROUP BY planning.id, planning.business_days, line.user_id, planning.date_from, planning.date_to
        )
        """)

report_account_analytic_planning_user()

class report_account_analytic_planning_account(osv.osv):
    _name = "report_account_analytic.planning.account"
    _description = "Planning by Account"
    _rec_name = 'account_id'
    _auto = False

    def _get_tasks(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm = users_obj.browse(cr, uid, uid, context=context).company_id.project_time_mode_id
        if tm and tm.factor:
            div = tm.factor
        else:
            div = 1.0
        tm2 = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm2 and tm2.factor:
            div2 = tm2.factor
        else:
            div2 = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                SELECT COALESCE(sum(tasks.remaining_hours),0)
                FROM project_task tasks
                WHERE tasks.planning_line_id IN (
                    SELECT id
                    FROM report_account_analytic_planning_line
                    WHERE planning_id = %s AND account_id=%s
                )""", (line.planning_id.id, line.account_id and line.account_id.id or None))
            result[line.id] = cr.fetchall()[0][0] / div * div2
        return result

    def _get_timesheets(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm2 = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm2 and tm2.factor:
            div2 = tm2.factor
        else:
            div2 = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            cr.execute("""
                SELECT SUM(unit_amount/uom.factor) FROM account_analytic_line acc
                LEFT JOIN product_uom uom ON (uom.id = acc.product_uom_id)
                WHERE acc.date>=%s and acc.date<=%s and acc.account_id=%s""", (line.planning_id.date_from, line.planning_id.date_to, line.account_id and line.account_id.id or None))
            res = cr.fetchall()[0][0]
            if res:
                result[line.id] = res * div2
            else:
                result[line.id] = 0
        return result

    _columns = {
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning'),
        'account_id': fields.many2one('account.analytic.account', 'Analytic account', readonly=True),
        'tasks': fields.function(_get_tasks, string='Remaining Tasks', help='This value is given by the sum of work remaining to do on the task for this planning, expressed in days.'),
        'plan_tasks': fields.float('Time Allocation of Tasks', readonly=True, help='This value is given by the sum of time allocation with the checkbox \'Assigned in Taks\' set to TRUE expressed in days.'),
        'plan_open': fields.float('Time Allocation without Tasks', readonly=True, help='This value is given by the sum of time allocation with the checkbox \'Assigned in Taks\' set to FALSE, expressed in days.'),
        'timesheet': fields.function(_get_timesheets, string='Timesheet', help='This value is given by the sum of all work encoded in the timesheet(s) between the \'Date From\' and \'Date To\' of the planning.'),
    }

    def init(self, cr):
        cr.execute(""" CREATE OR REPLACE VIEW report_account_analytic_planning_account AS (
          SELECT
            MIN(l.id) AS id,
            l.account_id AS account_id,
            SUM(l.amount) AS quantity,
            l.planning_id AS planning_id,
            ( SELECT SUM(line1.amount_in_base_uom)
              FROM report_account_analytic_planning_line line1
              WHERE
                ( SELECT COUNT(1)
                  FROM project_task task
                  WHERE task.planning_line_id = line1.id
                ) > 0
                AND l.account_id = line1.account_id
                AND l.planning_id = line1.planning_id
            ) AS plan_tasks,
            ( SELECT SUM(line1.amount_in_base_uom)
              FROM report_account_analytic_planning_line line1
              WHERE
                ( SELECT COUNT(1)
                  FROM project_task task
                  WHERE task.planning_line_id = line1.id
                ) = 0
                AND l.account_id = line1.account_id
                AND planning.id = line1.planning_id
            ) AS plan_open
          FROM report_account_analytic_planning_line l
          INNER JOIN report_account_analytic_planning planning ON planning.id=l.planning_id
          GROUP BY l.account_id, l.planning_id, planning.date_from, planning.date_to, planning.id
        )
        """)

report_account_analytic_planning_account()

class report_account_analytic_planning_stat(osv.osv):
    _name = "report_account_analytic.planning.stat"
    _description = "Planning stat"
    _rec_name = 'user_id'
    _auto = False
    _log_access = False
    _order = 'planning_id,user_id'

    def _sum_amount_real(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm2 = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm2 and tm2.factor:
            div2 = tm2.factor
        else:
            div2 = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            if line.user_id:
                cr.execute('''SELECT sum(acc.unit_amount/uom.factor) FROM account_analytic_line acc
                LEFT JOIN product_uom uom ON (uom.id = acc.product_uom_id)
WHERE user_id=%s and account_id=%s and date>=%s and date<=%s''', (line.user_id.id, line.account_id and line.account_id.id or None, line.planning_id.date_from, line.planning_id.date_to))
            else:
                cr.execute('SELECT sum(unit_amount) FROM account_analytic_line WHERE account_id=%s AND date>=%s AND date<=%s', (line.account_id and line.account_id.id or None, line.planning_id.date_from, line.planning_id.date_to))

        sum = cr.fetchone()
        if sum and sum[0]:
            result[line.id] = sum[0] * div2
        return result

    def _sum_amount_tasks(self, cr, uid, ids, name, args, context=None):
        users_obj = self.pool.get('res.users')
        result = {}
        tm = users_obj.browse(cr, uid, uid, context=context).company_id.project_time_mode_id
        if tm and tm.factor:
            div = tm.factor
        else:
            div = 1.0
        tm2 = users_obj.browse(cr, uid, uid, context=context).company_id.planning_time_mode_id
        if tm2 and tm2.factor:
            div2 = tm2.factor
        else:
            div2 = 1.0
        for line in self.browse(cr, uid, ids, context=context):
            where = ''
            if line.user_id:
                where = 'user_id=' + str(line.user_id.id) + ' and '
            cr.execute('''select
                    sum(planned_hours)
                FROM
                    project_task
                WHERE
                ''' + where + '''
                    project_id IN (select id from project_project where analytic_account_id=%s) AND
                    date_end>=%s AND
                    date_end<=%s''', (
                line.account_id and line.account_id.id or None,
                line.planning_id.date_from,
                line.planning_id.date_to)
            )
            sum = cr.fetchone()
            if sum and sum[0]:
                result[line.id] = sum[0] /div * div2
        return result

    _columns = {
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning', select=True),
        'user_id': fields.many2one('res.users', 'User', select=True),
        'manager_id': fields.many2one('res.users', 'Manager'),
        'account_id': fields.many2one('account.analytic.account', 'Account'),
        'sum_amount': fields.float('Planned Days', required=True),
        'sum_amount_real': fields.function(_sum_amount_real, string='Timesheet'),
        'sum_amount_tasks': fields.function(_sum_amount_tasks, string='Tasks'),
    }

    def init(self, cr):
        cr.execute("""
            create or replace view report_account_analytic_planning_stat as (
                SELECT
                    min(l.id) as id,
                    l.user_id as user_id,
                    a.user_id as manager_id,
                    l.account_id as account_id,
                    sum(l.amount/u.factor) as sum_amount,
                    l.planning_id
                FROM
                    report_account_analytic_planning_line l
                LEFT JOIN
                    report_account_analytic_planning a on (a.id = l.planning_id)
                LEFT JOIN
                    product_uom u on (l.amount_unit = u.id)
                GROUP BY
                    l.planning_id, l.user_id, l.account_id, a.user_id
            )
        """)

report_account_analytic_planning_stat()

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'planning_time_mode_id': fields.many2one('product.uom', 'Planning Time Unit',
            help='This will set the unit of measure used in plannings.',
        ),
    }
res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
