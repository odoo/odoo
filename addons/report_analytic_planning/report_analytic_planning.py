# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv

import time
import mx.DateTime

class report_account_analytic_planning(osv.osv):
    _name = "report_account_analytic.planning"
    _description = "Planning"
    _columns = {
        'name': fields.char('Planning Name', size=32, required=True),
        'user_id': fields.many2one('res.users', 'Responsible', required=True),
        'date_from':fields.date('Start Date', required=True),
        'date_to':fields.date('End Date', required=True),
        'line_ids': fields.one2many('report_account_analytic.planning.line', 'planning_id', 'Planning lines'),
        'stat_ids': fields.one2many('report_account_analytic.planning.stat', 'planning_id', 'Planning analysis', readonly=True),
        'stat_user_ids': fields.one2many('report_account_analytic.planning.stat.user', 'planning_id', 'Planning by user', readonly=True),
        'stat_account_ids': fields.one2many('report_account_analytic.planning.stat.account', 'planning_id', 'Planning by account', readonly=True),
        'state': fields.selection([('open','Open'),('done','Done')], 'Status', required=True)
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d'),
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: (mx.DateTime.now()+mx.DateTime.RelativeDateTime(months=1,day=1,days=-1)).strftime('%Y-%m-%d'),
        'user_id': lambda self,cr,uid,c: uid,
        'state': lambda *args: 'open'
    }
    _order = 'date_from desc'
report_account_analytic_planning()

class report_account_analytic_planning_line(osv.osv):
    _name = "report_account_analytic.planning.line"
    _description = "Planning Line"
    _rec_name = 'user_id'
    _columns = {
        'account_id':fields.many2one('account.analytic.account', 'Analytic account', required=True),
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning', required=True, ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'User'),
        'amount': fields.float('Quantity', required=True),
        'amount_unit':fields.many2one('product.uom', 'Qty UoM', required=True),
        'note':fields.text('Note', size=64),
    }
    _order = 'user_id,account_id'
report_account_analytic_planning_line()

class report_account_analytic_planning_stat_account(osv.osv):
    _name = "report_account_analytic.planning.stat.account"
    _description = "Planning account stat"
    _rec_name = 'account_id'
    _auto = False
    _log_access = False
    def _sum_amount_real(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context):
            cr.execute('select sum(unit_amount) from account_analytic_line where account_id=%s and date>=%s and date<=%s', (line.account_id.id,line.planning_id.date_from,line.planning_id.date_to))
            result[line.id] = cr.fetchone()[0]
        return result
    _columns = {
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning'),
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account', required=True),
        'quantity': fields.float('Planned', required=True),
        'sum_amount_real': fields.function(_sum_amount_real, method=True, string='Timesheet'),
    }
    def init(self, cr):
        cr.execute("""
            create or replace view report_account_analytic_planning_stat_account as (
                select
                    min(l.id) as id,
                    l.account_id as account_id,
                    sum(l.amount*u.factor) as quantity,
                    l.planning_id
                from
                    report_account_analytic_planning_line l
                left join
                    product_uom u on (l.amount_unit = u.id)
                group by
                    planning_id, account_id
            )
        """)
report_account_analytic_planning_stat_account()

class report_account_analytic_planning_stat(osv.osv):
    _name = "report_account_analytic.planning.stat"
    _description = "Planning stat"
    _rec_name = 'user_id'
    _auto = False
    _log_access = False
    def _sum_amount_real(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context):
            if line.user_id:
                cr.execute('select sum(unit_amount) from account_analytic_line where user_id=%s and account_id=%s and date>=%s and date<=%s', (line.user_id.id,line.account_id.id,line.planning_id.date_from,line.planning_id.date_to))
            else:
                cr.execute('select sum(unit_amount) from account_analytic_line where account_id=%s and date>=%s and date<=%s', (line.account_id.id,line.planning_id.date_from,line.planning_id.date_to))
            result[line.id] = cr.fetchone()[0]
        return result
    def _sum_amount_tasks(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context):
            where = ''
            sqlarg = ()
            if line.user_id:
                where='user_id=%s and '
                sqlarg = (line.user_id.id,)
            cr.execute('''select
                    sum(planned_hours)
                from
                    project_task
                where
                '''+where+'''
                    project_id in (select id from project_project where category_id=%s) and
                    date_close>=%s and
                    date_close<=%s''',
                        sqlarg + (
                           line.account_id.id,
                           line.planning_id.date_from,
                           line.planning_id.date_to))
            result[line.id] = cr.fetchone()[0]
        return result
    _columns = {
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning'),
        'user_id': fields.many2one('res.users', 'User'),
        'manager_id': fields.many2one('res.users', 'Manager'),
        'account_id': fields.many2one('account.analytic.account', 'Account', required=True),
        'sum_amount': fields.float('Planned hours', required=True),
        'sum_amount_real': fields.function(_sum_amount_real, method=True, string='Timesheet'),
        'sum_amount_tasks': fields.function(_sum_amount_tasks, method=True, string='Tasks'),
    }
    _order = 'planning_id,user_id'
    def init(self, cr):
        cr.execute("""
            create or replace view report_account_analytic_planning_stat as (
                select
                    min(l.id) as id,
                    l.user_id as user_id,
                    a.user_id as manager_id,
                    l.account_id as account_id,
                    sum(l.amount*u.factor) as sum_amount,
                    l.planning_id
                from
                    report_account_analytic_planning_line l
                left join
                    report_account_analytic_planning a on (a.id = l.planning_id)
                left join
                    product_uom u on (l.amount_unit = u.id)
                group by
                    l.planning_id, l.user_id, l.account_id, a.user_id
            )
        """)
report_account_analytic_planning_stat()

class report_account_analytic_planning_stat_user(osv.osv):
    _name = "report_account_analytic.planning.stat.user"
    _description = "Planning user stat"
    _rec_name = 'user_id'
    _auto = False
    _log_access = False
    def _sum_amount_real(self, cr, uid, ids, name, args, context):
        result = {}
        for line in self.browse(cr, uid, ids, context):
            result[line.id] = 0.0
            if line.user_id:
                cr.execute('select sum(unit_amount) from account_analytic_line where user_id=%s and date>=%s and date<=%s', (line.user_id.id,line.planning_id.date_from,line.planning_id.date_to))
                result[line.id] = cr.fetchone()[0]
        return result
    _columns = {
        'planning_id': fields.many2one('report_account_analytic.planning', 'Planning', required=True),
        'user_id': fields.many2one('res.users', 'User'),
        'quantity': fields.float('Planned', required=True),
        'sum_amount_real': fields.function(_sum_amount_real, method=True, string='Timesheet'),
    }
    def init(self, cr):
        cr.execute("""
            create or replace view report_account_analytic_planning_stat_user as (
                select
                    min(l.id) as id,
                    l.user_id as user_id,
                    sum(l.amount*u.factor) as quantity,
                    l.planning_id
                from
                    report_account_analytic_planning_line l
                left join
                    product_uom u on (l.amount_unit = u.id)
                group by
                    planning_id, user_id
            )
        """)
report_account_analytic_planning_stat_user()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

