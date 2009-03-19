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
from osv import osv,fields
import tools
import netsvc
from mx import DateTime
import time
import datetime
from tools.translate import _


def strToDate(dt):
        dt_date=datetime.date(int(dt[0:4]),int(dt[5:7]),int(dt[8:10]))
        return dt_date

# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------
class account_budget_post(osv.osv):
    _name = 'account.budget.post'
    _description = 'Budgetary Position'
    _columns = {
        'code': fields.char('Code', size=64, required=True),
        'name': fields.char('Name', size=256, required=True),
        'dotation_ids': fields.one2many('account.budget.post.dotation', 'post_id', 'Spreading'),
        'account_ids': fields.many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', 'Accounts'),
        'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'general_budget_id', 'Budget Lines'),
    }
    _defaults = {
    }

    def spread(self, cr, uid, ids, fiscalyear_id=False, amount=0.0):
        dobj = self.pool.get('account.budget.post.dotation')
        for o in self.browse(cr, uid, ids):
            # delete dotations for this post
            dobj.unlink(cr, uid, dobj.search(cr, uid, [('post_id','=',o.id)]))

            # create one dotation per period in the fiscal year, and spread the total amount/quantity over those dotations
            fy = self.pool.get('account.fiscalyear').browse(cr, uid, [fiscalyear_id])[0]
            num = len(fy.period_ids)
            for p in fy.period_ids:
                dobj.create(cr, uid, {'post_id': o.id, 'period_id': p.id, 'amount': amount/num})
        return True
account_budget_post()

class account_budget_post_dotation(osv.osv):
    def _tot_planned(self, cr, uid, ids,name,args,context):
        res={}
        for line in self.browse(cr, uid, ids):
            if line.period_id:
                obj_period=self.pool.get('account.period').browse(cr, uid,line.period_id.id)

                total_days=strToDate(obj_period.date_stop) - strToDate(obj_period.date_start)
                budget_id=line.post_id and line.post_id.id or False
                query="select id from crossovered_budget_lines where  general_budget_id= '"+ str(budget_id) + "' AND (date_from  >='"  +obj_period.date_start +"'  and date_from <= '"+obj_period.date_stop + "') OR (date_to  >='"  +obj_period.date_start +"'  and date_to <= '"+obj_period.date_stop + "') OR (date_from  <'"  +obj_period.date_start +"'  and date_to > '"+obj_period.date_stop + "')"
                cr.execute(query)
                res1=cr.fetchall()

                tot_planned=0.00
                for record in res1:
                    obj_lines = self.pool.get('crossovered.budget.lines').browse(cr, uid,record[0])
                    count_days = min(strToDate(obj_period.date_stop),strToDate(obj_lines.date_to)) - max(strToDate(obj_period.date_start), strToDate(obj_lines.date_from))
                    days_in_period = count_days.days +1
                    count_days = strToDate(obj_lines.date_to) - strToDate(obj_lines.date_from)
                    total_days_of_rec = count_days.days +1
                    tot_planned += obj_lines.planned_amount/total_days_of_rec* days_in_period
                res[line.id]=tot_planned
            else:
                res[line.id]=0.00
        return res

    _name = 'account.budget.post.dotation'
    _description = "Budget Dotation"
    _columns = {
        'name': fields.char('Name', size=64),
        'post_id': fields.many2one('account.budget.post', 'Item', select=True),
        'period_id': fields.many2one('account.period', 'Period'),
        'amount': fields.float('Amount', digits=(16,2)),
        'tot_planned':fields.function(_tot_planned,method=True, string='Total Planned Amount',type='float',store=True),
    }

account_budget_post_dotation()

class crossovered_budget(osv.osv):
    _name = "crossovered.budget"
    _description = "Budget"

    _columns = {
        'name': fields.char('Name', size=50, required=True,states={'done':[('readonly',True)]}),
        'code': fields.char('Code', size=20, required=True,states={'done':[('readonly',True)]}),
        'creating_user_id': fields.many2one('res.users','Responsible User'),
        'validating_user_id': fields.many2one('res.users','Validate User', readonly=True),
        'date_from': fields.date('Start Date',required=True,states={'done':[('readonly',True)]}),
        'date_to': fields.date('End Date',required=True,states={'done':[('readonly',True)]}),
        'state' : fields.selection([('draft','Draft'),('confirm','Confirmed'),('validate','Validated'),('done','Done'),('cancel', 'Cancelled')], 'Status', select=True, required=True, readonly=True),
        'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'crossovered_budget_id', 'Budget Lines',states={'done':[('readonly',True)]} ),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'creating_user_id': lambda self,cr,uid,context: uid,
    }

#   def action_set_to_draft(self, cr, uid, ids, *args):
#       self.write(cr, uid, ids, {'state': 'draft'})
#       wf_service = netsvc.LocalService('workflow')
#       for id in ids:
#           wf_service.trg_create(uid, self._name, id, cr)
#       return True

    def budget_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'confirm'
        })
        return True

    def budget_validate(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'validate',
            'validating_user_id': uid,
        })
        return True

    def budget_cancel(self, cr, uid, ids, *args):

        self.write(cr, uid, ids, {
            'state':'cancel'
        })
        return True

    def budget_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {
            'state':'done'
        })
        return True

crossovered_budget()

class crossovered_budget_lines(osv.osv):

    def _prac_amt(self, cr, uid, ids,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            acc_ids = [x.id for x in line.general_budget_id.account_ids]
            if not acc_ids:
                raise osv.except_osv(_('Error!'),_("The General Budget '%s' has no Accounts!") % str(line.general_budget_id.name))
            date_to = line.date_to
            date_from = line.date_from
            if context.has_key('wizard_date_from'):
                date_from = context['wizard_date_from']
            if context.has_key('wizard_date_to'):
                date_to = context['wizard_date_to']

            cr.execute("select sum(amount) from account_analytic_line where account_id=%%s and (date "
                       "between to_date(%%s,'yyyy-mm-dd') and to_date(%%s,'yyyy-mm-dd')) and "
                       "general_account_id in (%s)" % ",".join(map(str,acc_ids)), (line.analytic_account_id.id, date_from, date_to ))
            result = cr.fetchone()[0]
            if result is None:
                result = 0.00
            res[line.id] = result
        return res

    def _prac(self, cr, uid, ids,name,args,context):
        res={}
        for line in self.browse(cr, uid, ids):
            res[line.id]=self._prac_amt(cr,uid,[line.id],context=context)[line.id]

        return res

    def _theo_amt(self, cr, uid, ids,context={}):
        res = {}
        for line in self.browse(cr, uid, ids):
            today=datetime.datetime.today()
            date_to = today.strftime("%Y-%m-%d")
            date_from = line.date_from
            if context.has_key('wizard_date_from'):
                date_from = context['wizard_date_from']
            if context.has_key('wizard_date_to'):
                date_to = context['wizard_date_to']

            if line.paid_date:
                if strToDate(line.date_to)<=strToDate(line.paid_date):
                    theo_amt=0.00
                else:
                    theo_amt=line.planned_amount
            else:
                total=strToDate(line.date_to) - strToDate(line.date_from)
                elapsed = min(strToDate(line.date_to),strToDate(date_to)) - max(strToDate(line.date_from),strToDate(date_from))
                if strToDate(date_to) < strToDate(line.date_from):
                    elapsed = strToDate(date_to) - strToDate(date_to)

                theo_amt=float(elapsed.days/float(total.days))*line.planned_amount

            res[line.id]=theo_amt
        return res

    def _theo(self, cr, uid, ids,name,args,context):
        res={}
        for line in self.browse(cr, uid, ids):
            res[line.id]=self._theo_amt(cr,uid,[line.id],context=context)[line.id]

        return res

    def _perc(self, cr, uid, ids,name,args,context):
        res = {}
        for line in self.browse(cr, uid, ids):
            if line.theoritical_amount<>0.00:
                res[line.id]=float(line.practical_amount / line.theoritical_amount)*100
            else:
                res[line.id]=0.00
        return res
    _name="crossovered.budget.lines"
    _description = "Budget Lines"
    _columns = {
        'crossovered_budget_id': fields.many2one('crossovered.budget', 'Budget', ondelete='cascade', select=True, required=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account',required=True),
        'general_budget_id': fields.many2one('account.budget.post', 'Budgetary Position',required=True),
        'date_from': fields.date('Start Date',required=True),
        'date_to': fields.date('End Date',required=True),
        'paid_date': fields.date('Paid Date'),
        'planned_amount':fields.float('Planned Amount',required=True,digits=(16,2)),
        'practical_amount':fields.function(_prac,method=True, string='Practical Amount',type='float',digits=(16,2)),
        'theoritical_amount':fields.function(_theo,method=True, string='Theoritical Amount',type='float',digits=(16,2)),
        'percentage':fields.function(_perc,method=True, string='Percentage',type='float'),
    }
crossovered_budget_lines()

class account_analytic_account(osv.osv):
    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'

    _columns = {
    'crossovered_budget_line': fields.one2many('crossovered.budget.lines', 'analytic_account_id', 'Budget Lines'),
    }

account_analytic_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

