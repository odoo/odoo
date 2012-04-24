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
import datetime

from osv import fields, osv
import pooler
import tools
from tools.translate import _

class project_project(osv.osv):
    _inherit = 'project.project'

    def _to_invoice(self, cr, uid, ids,field_name, arg, context=None):
        res = {}
        aal_pool = self.pool.get("account.analytic.line")
        for project in self.browse(cr,uid,ids,context=context):
            line_ids = aal_pool.search(cr, uid, [('account_id','=',project.analytic_account_id.id),('to_invoice','=',1),('invoice_id','=',False)])
            res[project.id] = {
                    'amt_to_invoice': 0.0,
                    'hrs_to_invoice': 0.0,
                }
            if line_ids:
                amt_to_invoice,hrs_to_invoice = 0.0,0.0
                for line in aal_pool.browse(cr,uid,line_ids,context=context):
                    amt_to_invoice += line.amount
                    hrs_to_invoice += line.unit_amount
                res[project.id]['amt_to_invoice'] = (amt_to_invoice)*-1
                res[project.id]['hrs_to_invoice'] = hrs_to_invoice
            
        return res
    
    def _compute_timesheet(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        aal_pool=self.pool.get('account.analytic.line')
        for project in self.browse(cr, uid, ids, context=context):
            timesheet = aal_pool.search(cr, uid, [("account_id","=", project.analytic_account_id.id)])
            res[project.id] = len(timesheet)
        return res

    _columns = {
        'timesheets' : fields.boolean('Timesheets',help = "If you check this field timesheets appears in kanban view"),
        'amt_to_invoice': fields.function(_to_invoice,string="Amount to Invoice",multi="sums"),
        'hrs_to_invoice': fields.function(_to_invoice,string="Hours to Invoice",multi="sums"),
        'total_timesheet': fields.function(_compute_timesheet , type='integer',string="Issue"),
    }
    _defaults = {
        'timesheets' : True,
    }

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        res = super(project_project, self).onchange_partner_id(cr, uid, ids, part, context)
        if part and res and ('value' in res):
            # set Invoice Task Work to 100%
            data_obj = self.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, uid, 'hr_timesheet_invoice', 'timesheet_invoice_factor1')
            if data_id:
                factor_id = data_obj.browse(cr, uid, data_id).res_id
                res['value'].update({'to_invoice': factor_id})
        return res

    def open_timesheets(self, cr, uid, ids, context=None):
        #Open the View for the Timesheet of the project
        """
        This opens Timesheets views
        @return :Dictionary value for timesheet view
        """
        if context is None:
            context = {}
        if ids:
            project = self.browse(cr, uid, ids[0], context=context)
            context = dict(context, search_default_account_id=project.analytic_account_id.id)
        return {
                'name': _('Bill Tasks Works'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.analytic.line',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'nodestroy': True
            }

project_project()

class project_work(osv.osv):
    _inherit = "project.task.work"

    def get_user_related_details(self, cr, uid, user_id):
        res = {}
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', user_id)])
        if not emp_id:
            user_name = self.pool.get('res.users').read(cr, uid, [user_id], ['name'])[0]['name']
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No employee defined for user "%s". You must create one.')% (user_name,))
        emp = self.pool.get('hr.employee').browse(cr, uid, emp_id[0])
        if not emp.product_id:
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No product defined on the related employee.\nFill in the timesheet tab of the employee form.'))

        if not emp.journal_id:
            raise osv.except_osv(_('Bad Configuration !'),
                 _('No journal defined on the related employee.\nFill in the timesheet tab of the employee form.'))

        a = emp.product_id.product_tmpl_id.property_account_expense.id
        if not a:
            a = emp.product_id.categ_id.property_account_expense_categ.id
            if not a:
                raise osv.except_osv(_('Bad Configuration !'),
                        _('No product and product category property account defined on the related employee.\nFill in the timesheet tab of the employee form.'))
        res['product_id'] = emp.product_id.id
        res['journal_id'] = emp.journal_id.id
        res['general_account_id'] = a
        res['product_uom_id'] = emp.product_id.uom_id.id
        return res

    def create(self, cr, uid, vals, *args, **kwargs):
        obj_timesheet = self.pool.get('hr.analytic.timesheet')
        project_obj = self.pool.get('project.project')
        task_obj = self.pool.get('project.task')
        uom_obj = self.pool.get('product.uom')
        
        vals_line = {}
        context = kwargs.get('context', {})
        if not context.get('no_analytic_entry',False):
            obj_task = task_obj.browse(cr, uid, vals['task_id'])
            result = self.get_user_related_details(cr, uid, vals.get('user_id', uid))
            vals_line['name'] = '%s: %s' % (tools.ustr(obj_task.name), tools.ustr(vals['name']) or '/')
            vals_line['user_id'] = vals['user_id']
            vals_line['product_id'] = result['product_id']
            vals_line['date'] = vals['date'][:10]
            
            #calculate quantity based on employee's product's uom 
            vals_line['unit_amount'] = vals['hours']

            default_uom = self.pool.get('res.users').browse(cr, uid, uid).company_id.project_time_mode_id.id
            if result['product_uom_id'] != default_uom:
                vals_line['unit_amount'] = uom_obj._compute_qty(cr, uid, default_uom, vals['hours'], result['product_uom_id'])
            acc_id = obj_task.project_id and obj_task.project_id.analytic_account_id.id or False
            if acc_id:
                vals_line['account_id'] = acc_id
                res = obj_timesheet.on_change_account_id(cr, uid, False, acc_id)
                if res.get('value'):
                    vals_line.update(res['value'])
                vals_line['general_account_id'] = result['general_account_id']
                vals_line['journal_id'] = result['journal_id']
                vals_line['amount'] = 0.0
                vals_line['product_uom_id'] = result['product_uom_id']
                amount = vals_line['unit_amount']
                prod_id = vals_line['product_id']
                unit = False
                timeline_id = obj_timesheet.create(cr, uid, vals=vals_line, context=context)

                # Compute based on pricetype
                amount_unit = obj_timesheet.on_change_unit_amount(cr, uid, timeline_id,
                    prod_id, amount, False, unit, vals_line['journal_id'], context=context)
                if amount_unit and 'amount' in amount_unit.get('value',{}):
                    updv = { 'amount': amount_unit['value']['amount'] }
                    obj_timesheet.write(cr, uid, [timeline_id], updv, context=context)
                vals['hr_analytic_timesheet_id'] = timeline_id
        return super(project_work,self).create(cr, uid, vals, *args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        timesheet_obj = self.pool.get('hr.analytic.timesheet')
        project_obj = self.pool.get('project.project')
        uom_obj = self.pool.get('product.uom')
        result = {}
        
        if isinstance(ids, (long, int)):
            ids = [ids,]

        for task in self.browse(cr, uid, ids, context=context):
            line_id = task.hr_analytic_timesheet_id
            if not line_id:
                # if a record is deleted from timesheet, the line_id will become
                # null because of the foreign key on-delete=set null
                continue
            vals_line = {}
            if 'name' in vals:
                vals_line['name'] = '%s: %s' % (tools.ustr(task.task_id.name), tools.ustr(vals['name']) or '/')
            if 'user_id' in vals:
                vals_line['user_id'] = vals['user_id']
                result = self.get_user_related_details(cr, uid, vals['user_id'])
                for fld in ('product_id', 'general_account_id', 'journal_id', 'product_uom_id'):
                    if result.get(fld, False):
                        vals_line[fld] = result[fld]
                        
            if 'date' in vals:
                vals_line['date'] = vals['date'][:10]
            if 'hours' in vals:
                default_uom = self.pool.get('res.users').browse(cr, uid, uid).company_id.project_time_mode_id.id
                vals_line['unit_amount'] = vals['hours']
                prod_id = vals_line.get('product_id', line_id.product_id.id) # False may be set

                if result.get('product_uom_id',False) and (not result['product_uom_id'] == default_uom):
                    vals_line['unit_amount'] = uom_obj._compute_qty(cr, uid, default_uom, vals['hours'], result['product_uom_id'])
                    
                # Compute based on pricetype
                amount_unit = timesheet_obj.on_change_unit_amount(cr, uid, line_id.id,
                    prod_id=prod_id, company_id=False,
                    unit_amount=vals_line['unit_amount'], unit=False, journal_id=vals_line['journal_id'], context=context)

                if amount_unit and 'amount' in amount_unit.get('value',{}):
                    vals_line['amount'] = amount_unit['value']['amount']

            self.pool.get('hr.analytic.timesheet').write(cr, uid, [line_id.id], vals_line, context=context)
            
        return super(project_work,self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        hat_obj = self.pool.get('hr.analytic.timesheet')
        hat_ids = []
        for task in self.browse(cr, uid, ids):
            if task.hr_analytic_timesheet_id:
                hat_ids.append(task.hr_analytic_timesheet_id.id)
#            delete entry from timesheet too while deleting entry to task.
        if hat_ids:
            hat_obj.unlink(cr, uid, hat_ids, *args, **kwargs)
        return super(project_work,self).unlink(cr, uid, ids, *args, **kwargs)

    _columns={
        'hr_analytic_timesheet_id':fields.many2one('hr.analytic.timesheet','Related Timeline Id', ondelete='set null'),
    }

project_work()

class task(osv.osv):
    _inherit = "project.task"

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for task_obj in self.browse(cr, uid, ids, *args, **kwargs):
            if task_obj.work_ids:
                work_ids = [x.id for x in task_obj.work_ids]
                self.pool.get('project.task.work').unlink(cr, uid, work_ids, *args, **kwargs)

        return super(task,self).unlink(cr, uid, ids, *args, **kwargs)

    def write(self, cr, uid, ids,vals,context=None):
        if context is None:
            context = {}
        if vals.get('project_id',False) or vals.get('name',False):
            vals_line = {}
            hr_anlytic_timesheet = self.pool.get('hr.analytic.timesheet')
            task_obj_l = self.browse(cr, uid, ids, context=context)
            if vals.get('project_id',False):
                project_obj = self.pool.get('project.project').browse(cr, uid, vals['project_id'], context=context)
                acc_id = project_obj.analytic_account_id.id

            for task_obj in task_obj_l:
                if len(task_obj.work_ids):
                    for task_work in task_obj.work_ids:
                        if not task_work.hr_analytic_timesheet_id:
                            continue
                        line_id = task_work.hr_analytic_timesheet_id.id
                        if vals.get('project_id',False):
                            vals_line['account_id'] = acc_id
                        if vals.get('name',False):
                            vals_line['name'] = '%s: %s' % (tools.ustr(vals['name']), tools.ustr(task_work.name) or '/')
                        hr_anlytic_timesheet.write(cr, uid, [line_id], vals_line, {})
        return super(task,self).write(cr, uid, ids, vals, context)

task()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    def unlink(self, cursor, user, ids, context=None):
        parnter_id=self.pool.get('project.project').search(cursor, user, [('partner_id', 'in', ids)])
        if parnter_id:
            raise osv.except_osv(_('Invalid action !'), _('You cannot delete a partner which is assigned to project, we suggest you to uncheck the active box!'))
        return super(res_partner,self).unlink(cursor, user, ids,
                context=context)
res_partner()

class account_analytic_line(osv.osv):
   _inherit = "account.analytic.line"
   def on_change_account_id(self, cr, uid, ids, account_id):
       res = {}
       if not account_id:
           return res
       res.setdefault('value',{})
       acc = self.pool.get('account.analytic.account').browse(cr, uid, account_id)
       st = acc.to_invoice.id
       res['value']['to_invoice'] = st or False
       if acc.state == 'close' or acc.state == 'cancelled':
           raise osv.except_osv(_('Invalid Analytic Account !'), _('You cannot select a Analytic Account which is in Close or Cancelled state'))
       return res  
account_analytic_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
