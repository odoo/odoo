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
from operator import itemgetter
import re
import copy

from openerp.exceptions import Warning, AccessError, MissingError, except_orm
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _

class project_project(osv.osv):
    _inherit = 'project.project'

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
        
    _defaults = {
        'invoice_on_timesheets': True,
    }

    def open_timesheets(self, cr, uid, ids, context=None):
        """ open Timesheets view """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        project = self.browse(cr, uid, ids[0], context)
        view_context = {
            'search_default_account_id': [project.analytic_account_id.id],
            'default_account_id': project.analytic_account_id.id,
        }
        help = _("""<p class="oe_view_nocontent_create">Record your timesheets for the project '%s'.</p>""") % (project.name,)
        try:
            if project.to_invoice and project.partner_id:
                help+= _("""<p>Timesheets on this project may be invoiced to %s, according to the terms defined in the contract.</p>""" ) % (project.partner_id.name,)
        except:
            # if the user do not have access rights on the partner
            pass

        res = mod_obj.get_object_reference(cr, uid, 'hr_timesheet', 'act_hr_timesheet_line_evry1_all_form')
        id = res and res[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['name'] = _('Timesheets')
        result['context'] = view_context
        result['help'] = help
        return result


class project_work(osv.osv):
    _inherit = "project.task.work"

    def get_user_related_details(self, cr, uid, user_id):
        res = {}
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', user_id)])
        if not emp_id:
            user_name = self.pool.get('res.users').read(cr, uid, [user_id], ['name'])[0]['name']
            raise osv.except_osv(_('Bad Configuration!'),
                 _('Please define employee for user "%s". You must create one.')% (user_name,))
        emp = emp_obj.browse(cr, uid, emp_id[0])
        if not emp.product_id:
            raise osv.except_osv(_('Bad Configuration!'),
                 _('Please define product and product category property account on the related employee.\nFill in the HR Settings tab of the employee form.'))

        if not emp.journal_id:
            raise osv.except_osv(_('Bad Configuration!'),
                 _('Please define journal on the related employee.\nFill in the timesheet tab of the employee form.'))

        acc_id = emp.product_id.property_account_expense.id
        if not acc_id:
            acc_id = emp.product_id.categ_id.property_account_expense_categ.id
            if not acc_id:
                raise osv.except_osv(_('Bad Configuration!'),
                        _('Please define product and product category property account on the related employee.\nFill in the timesheet tab of the employee form.'))

        res['product_id'] = emp.product_id.id
        res['journal_id'] = emp.journal_id.id
        res['general_account_id'] = acc_id
        res['product_uom_id'] = emp.product_id.uom_id.id
        return res

    def _create_analytic_entries(self, cr, uid, vals, context):
        """Create the hr analytic timesheet from project task work"""
        timesheet_obj = self.pool['hr.analytic.timesheet']
        task_obj = self.pool['project.task']

        vals_line = {}
        timeline_id = False
        acc_id = False

        task_obj = task_obj.browse(cr, uid, vals['task_id'], context=context)
        result = self.get_user_related_details(cr, uid, vals.get('user_id', uid))
        vals_line['name'] = '%s: %s' % (tools.ustr(task_obj.name), tools.ustr(vals['name'] or '/'))
        vals_line['user_id'] = vals['user_id']
        vals_line['product_id'] = result['product_id']
        if vals.get('date'):
            timestamp = datetime.datetime.strptime(vals['date'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
            ts = fields.datetime.context_timestamp(cr, uid, timestamp, context)
            vals_line['date'] = ts.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)

        # Calculate quantity based on employee's product's uom
        vals_line['unit_amount'] = vals['hours']

        default_uom = self.pool['res.users'].browse(cr, uid, uid, context=context).company_id.project_time_mode_id.id
        if result['product_uom_id'] != default_uom:
            vals_line['unit_amount'] = self.pool['product.uom']._compute_qty(cr, uid, default_uom, vals['hours'], result['product_uom_id'])
        acc_id = task_obj.project_id and task_obj.project_id.analytic_account_id.id or acc_id
        if acc_id:
            vals_line['account_id'] = acc_id
            res = timesheet_obj.on_change_account_id(cr, uid, False, acc_id)
            if res.get('value'):
                vals_line.update(res['value'])
            vals_line['general_account_id'] = result['general_account_id']
            vals_line['journal_id'] = result['journal_id']
            vals_line['amount'] = 0.0
            vals_line['product_uom_id'] = result['product_uom_id']
            amount = vals_line['unit_amount']
            prod_id = vals_line['product_id']
            unit = False
            timeline_id = timesheet_obj.create(cr, uid, vals=vals_line, context=context)

            # Compute based on pricetype
            amount_unit = timesheet_obj.on_change_unit_amount(cr, uid, timeline_id,
                prod_id, amount, False, unit, vals_line['journal_id'], context=context)
            if amount_unit and 'amount' in amount_unit.get('value',{}):
                updv = { 'amount': amount_unit['value']['amount'] }
                timesheet_obj.write(cr, uid, [timeline_id], updv, context=context)

        return timeline_id

    def create(self, cr, uid, vals, *args, **kwargs):
        context = kwargs.get('context', {})
        if not context.get('no_analytic_entry',False):
            vals['hr_analytic_timesheet_id'] = self._create_analytic_entries(cr, uid, vals, context=context)
        return super(project_work,self).create(cr, uid, vals, *args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        """
        When a project task work gets updated, handle its hr analytic timesheet.
        """
        if context is None:
            context = {}
        timesheet_obj = self.pool.get('hr.analytic.timesheet')
        uom_obj = self.pool.get('product.uom')
        result = {}

        if isinstance(ids, (long, int)):
            ids = [ids]

        for task in self.browse(cr, uid, ids, context=context):
            line_id = task.hr_analytic_timesheet_id
            if not line_id:
                # if a record is deleted from timesheet, the line_id will become
                # null because of the foreign key on-delete=set null
                continue

            vals_line = {}
            if 'name' in vals:
                vals_line['name'] = '%s: %s' % (tools.ustr(task.task_id.name), tools.ustr(vals['name'] or '/'))
            if 'user_id' in vals:
                vals_line['user_id'] = vals['user_id']
            if 'date' in vals:
                vals_line['date'] = vals['date'][:10]
            if 'hours' in vals:
                vals_line['unit_amount'] = vals['hours']
                prod_id = vals_line.get('product_id', line_id.product_id.id) # False may be set

                # Put user related details in analytic timesheet values
                details = self.get_user_related_details(cr, uid, vals.get('user_id', task.user_id.id))
                for field in ('product_id', 'general_account_id', 'journal_id', 'product_uom_id'):
                    if details.get(field, False):
                        vals_line[field] = details[field]

                # Check if user's default UOM differs from product's UOM
                user_default_uom_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.project_time_mode_id.id
                if details.get('product_uom_id', False) and details['product_uom_id'] != user_default_uom_id:
                    vals_line['unit_amount'] = uom_obj._compute_qty(cr, uid, user_default_uom_id, vals['hours'], details['product_uom_id'])

                # Compute based on pricetype
                amount_unit = timesheet_obj.on_change_unit_amount(cr, uid, line_id.id,
                    prod_id=prod_id, company_id=False,
                    unit_amount=vals_line['unit_amount'], unit=False, journal_id=vals_line['journal_id'], context=context)

                if amount_unit and 'amount' in amount_unit.get('value',{}):
                    vals_line['amount'] = amount_unit['value']['amount']

            if vals_line:
                self.pool.get('hr.analytic.timesheet').write(cr, uid, [line_id.id], vals_line, context=context)

        return super(project_work,self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, *args, **kwargs):
        hat_obj = self.pool.get('hr.analytic.timesheet')
        hat_ids = []
        for task in self.browse(cr, uid, ids):
            if task.hr_analytic_timesheet_id:
                hat_ids.append(task.hr_analytic_timesheet_id.id)
        # Delete entry from timesheet too while deleting entry to task.
        if hat_ids:
            hat_obj.unlink(cr, uid, hat_ids, *args, **kwargs)
        return super(project_work,self).unlink(cr, uid, ids, *args, **kwargs)

    _columns={
        'hr_analytic_timesheet_id':fields.many2one('hr.analytic.timesheet','Related Timeline Id', ondelete='set null'),
    }


class task(osv.osv):
    _inherit = "project.task"

    #TO REMOVE: Once task 'Remove worklogs 8846' is merged
    _columns = {
        'timesheet_ids': fields.one2many('hr.analytic.timesheet', 'task_id', 'Timesheets'),
        'analytic_account_id': fields.related('project_id', 'analytic_account_id',
                    type='many2one', relation='account.analytic.account',string='Analytic Account', store=True),
    }

    def unlink(self, cr, uid, ids, *args, **kwargs):
        for task_obj in self.browse(cr, uid, ids, *args, **kwargs):
            if task_obj.work_ids:
                work_ids = [x.id for x in task_obj.work_ids]
                self.pool.get('project.task.work').unlink(cr, uid, work_ids, *args, **kwargs)

        return super(task,self).unlink(cr, uid, ids, *args, **kwargs)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        task_work_obj = self.pool['project.task.work']
        acc_id = False
        missing_analytic_entries = {}

        if vals.get('project_id',False) or vals.get('name',False):
            vals_line = {}
            hr_anlytic_timesheet = self.pool.get('hr.analytic.timesheet')
            if vals.get('project_id',False):
                project_obj = self.pool.get('project.project').browse(cr, uid, vals['project_id'], context=context)
                acc_id = project_obj.analytic_account_id.id

            for task_obj in self.browse(cr, uid, ids, context=context):
                if len(task_obj.work_ids):
                    for task_work in task_obj.work_ids:
                        if not task_work.hr_analytic_timesheet_id:
                            if acc_id :
                                # missing timesheet activities to generate
                                missing_analytic_entries[task_work.id] = {
                                    'name' : task_work.name,
                                    'user_id' : task_work.user_id.id,
                                    'date' : task_work.date and task_work.date[:10] or False,
                                    'account_id': acc_id,
                                    'hours' : task_work.hours,
                                    'task_id' : task_obj.id
                                }
                            continue
                        line_id = task_work.hr_analytic_timesheet_id.id
                        if vals.get('project_id',False):
                            vals_line['account_id'] = acc_id
                        if vals.get('name',False):
                            vals_line['name'] = '%s: %s' % (tools.ustr(vals['name']), tools.ustr(task_work.name) or '/')
                        hr_anlytic_timesheet.write(cr, uid, [line_id], vals_line, {})

        res = super(task,self).write(cr, uid, ids, vals, context)

        for task_work_id, analytic_entry in missing_analytic_entries.items():
            timeline_id = task_work_obj._create_analytic_entries(cr, uid, analytic_entry, context=context)
            task_work_obj.write(cr, uid, task_work_id, {'hr_analytic_timesheet_id' : timeline_id}, context=context)

        return res


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def unlink(self, cursor, user, ids, context=None):
        parnter_id=self.pool.get('project.project').search(cursor, user, [('partner_id', 'in', ids)])
        if parnter_id:
            raise osv.except_osv(_('Invalid Action!'), _('You cannot delete a partner which is assigned to project, but you can uncheck the active box.'))
        return super(res_partner,self).unlink(cursor, user, ids,
                context=context)


class account_analytic_line(osv.osv):
   _inherit = "account.analytic.line"

   def get_product(self, cr, uid, context=None):
        emp_obj = self.pool.get('hr.employee')
        emp_ids = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
        if emp_ids:
            employee = emp_obj.browse(cr, uid, emp_ids, context=context)[0]
            if employee.product_id:return employee.product_id.id
        return False
   
   _defaults = {'product_id': get_product,}
   
   def on_change_account_id(self, cr, uid, ids, account_id):
       res = {}
       if not account_id:
           return res
       res.setdefault('value',{})
       acc = self.pool.get('account.analytic.account').browse(cr, uid, account_id)
       st = acc.to_invoice.id
       res['value']['to_invoice'] = st or False
       if acc.state == 'close' or acc.state == 'cancelled':
           raise osv.except_osv(_('Invalid Analytic Account!'), _('You cannot select a Analytic Account which is in Close or Cancelled state.'))
       return res

class hr_analytic_timesheet(osv.Model):
    _inherit = 'hr.analytic.timesheet'
    _description = 'hr analytic timesheet'

    #TO REMOVE task_id: Once task 'Remove worklogs 8846' is merged
    _columns = {
        'task_id' : fields.many2one('project.task', 'Task'),
        'reference_id': fields.char('Anlytic Timesheet Reference'), #Use session_id to generate referenece_id
        #'session_id': fields.many2one('project.timesheet.session', 'Project Timesheet Session ID'), #We can add session_id field in records while sync so that we can have idea which reods is sync with which session
    }

    def get_user_related_details(self, cr, uid, user_id):
        res = {}
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', user_id)])
        if not emp_id:
            user_name = self.pool.get('res.users').read(cr, uid, [user_id], ['name'])[0]['name']
            raise osv.except_osv(_('Bad Configuration!'),
                 _('Please define employee for user "%s". You must create one.')% (user_name,))
        emp = emp_obj.browse(cr, uid, emp_id[0])
        if not emp.product_id:
            raise osv.except_osv(_('Bad Configuration!'),
                 _('Please define product and product category property account on the related employee.\nFill in the HR Settings tab of the employee form.'))

        if not emp.journal_id:
            raise osv.except_osv(_('Bad Configuration!'),
                 _('Please define journal on the related employee.\nFill in the timesheet tab of the employee form.'))

        acc_id = emp.product_id.property_account_expense.id
        if not acc_id:
            acc_id = emp.product_id.categ_id.property_account_expense_categ.id
            if not acc_id:
                raise osv.except_osv(_('Bad Configuration!'),
                        _('Please define product and product category property account on the related employee.\nFill in the timesheet tab of the employee form.'))

        res['product_id'] = emp.product_id.id
        res['journal_id'] = emp.journal_id.id
        res['general_account_id'] = acc_id
        res['product_uom_id'] = emp.product_id.uom_id.id
        return res

    def load_data(self, cr, uid, domain=None, fields=None, context=None):
        activities = []
        analytic_lines = self.search_read(cr, uid, domain=domain, fields=fields, context=context)
        account_ids = [x['account_id'][0] for x in analytic_lines if x['account_id']]
        account_ids = list(set(account_ids))
        projects = self.pool.get('project.project').search_read(cr, uid, domain=[('analytic_account_id', 'in', account_ids)], fields=['name', 'analytic_account_id'], context=context)
        #TODO: Use list comprehension next two loops
        for project in projects:
            for analytic_line in analytic_lines:
                if analytic_line.get('account_id')[0] == project.get('analytic_account_id')[0]:
                    analytic_line['project_id'] = (project['id'], project['name'])
        analytic_lines = filter(lambda x: x.get('project_id'), analytic_lines) #Filter records which doesn't have project_id

        return analytic_lines

    def sync_data(self, cr, uid, datas, load_data_domain=None, context=None):
        """
        This method synchronized the data given by Project Timesheet UI,
        the method will create Save Point and then try to create project if record having new project and same way it tries to create task if task is new,
        else if will assign existing project_id and task_id in value gooing to prepare, after preparing values it will call create/write of hr.analytic.timesheet based on command and reference_id,
        data will have unique reference_id, this reference_id is checked before record is sync with database,
        here we will check if reference_id is already there then even though record having command=0(i.e. create) do not create record,
        if record having reference_id then write the record, if record having command=0 and there is no reference_id match then and only then create record,
        Once record has been sync then reload the data and provide new data to client so that client updates localstorage with new 30 day's data.
        """
        print "\n\ndatas are inside hr_analytic_timesheet ::: ", context, datas
        result = {}
        if not context:
            context = {}
        user_related_details = {}
        try:
            user_related_details = self.get_user_related_details(cr, uid, uid)
        except Exception, e:
            raise e

        virtual_id_regex = r"^virtual_id_.*$"
        pattern = re.compile(virtual_id_regex)
        project_obj = self.pool.get('project.project')
        task_obj = self.pool.get('project.task')
        uom_obj = self.pool.get('product.uom')
        missing_project_id = []
        missing_task_id = []
        fail_records = []

        def replace_virtual_id(field, virtual_id, real_id):
            for record in datas:
                if record.get(field) and isinstance(record.get(field), list) and record[field][0] == virtual_id:
                    record[field][0] = real_id

        for record in datas:
            try:
                cr.execute('SAVEPOINT sync_record')
                project_id = False
                new_project_id = False
                task_id = False
                new_task_id = False
                vals_line = {}
                submitted_line = None
                current_record = copy.deepcopy(record)
                if not record.get('project_id'):
                    raise except_orm(_("Value Missing"), _("Project ID is required, Please add value in Project Field."))
                #TO Check if reference_id of record is available in database, if yes then update the record else create
                #Check is basically for scenario where record is already sync but server doesn't respons to client and client did not updated localstorage
                #In such case we will check based on reference_id, generated by client
                is_submitted_id = self.search(cr, uid, [('reference_id', '=', record.get('reference_id'))], context=context)
                if is_submitted_id:
                    submitted_line = self.browse(cr, uid, is_submitted_id[0], context=context)
                print "\n\nrecord command is ::: ", record['command'], is_submitted_id, record['reference_id']
                if pattern.match(str(record['project_id'][0])) and (not is_submitted_id or record['command'] == 1):
                    project_id = project_obj.create(cr, uid, {'name': record['project_id'][1]}, context=context)
                    new_project_id = True
                    print "Trying to create project ::: ", project_id
                elif pattern.match(str(record['project_id'][0])) and is_submitted_id:
                    #If record is already submitted in previous sync then Fetch project_id based on is_submitted_id -> account_id
                    analytic_account_id = submitted_line.account_id and submitted_line.account_id.id
                    if not analytic_account_id:
                        continue
                    project_ids = project_obj.search(cr, uid, [('analytic_account_id', '=', analytic_account_id)], context=context)
                    if not project_ids:
                        continue
                    project_id = project_ids[0]
                else:
                    project_id = record['project_id'][0]
                project_record = project_obj.browse(cr, uid, project_id, context=context)
                if project_id in missing_project_id or not project_record:
                    missing_project_id.append(project_id)
                    continue
                if record.get('task_id'):
                    if pattern.match(str(record['task_id'][0])) and (not is_submitted_id or record['command'] == 1):
                        task_id = task_obj.create(cr, uid, {'name': record['task_id'][1], 'project_id': project_id}, context=context)
                        new_task_id = True
                    elif pattern.match(str(record['task_id'][0])) and is_submitted_id:
                        #Fetch task_id based on is_submitted_id
                        task_id = submitted_line.task_id.id
                    else:
                        task_id = record['task_id'][0]
                    record['task_id'] = task_id
                    if task_id and task_id in missing_task_id and not task_obj.search(cr, uid, [('id', '=', task_id)], context=context):
                        missing_task_id.append(task_id)
                        continue

                #vals_line['name'] = '%s: %s' % (tools.ustr(task_obj.name), tools.ustr(vals['name'] or '/'))
                vals_line['name'] = record['name']
                vals_line['reference_id'] = record['reference_id']
                vals_line['task_id'] = record.get('task_id', False)
                vals_line['user_id'] = record['user_id'][0] if isinstance(record['user_id'], tuple) else record['user_id']
                vals_line['product_id'] = user_related_details['product_id']
                vals_line['date'] = record['date'][:10]
                # Calculate quantity based on employee's product's uom
                vals_line['unit_amount'] = record['unit_amount']
    
                account_id = project_record.analytic_account_id.id
                #TO Remove: Once we load hr.analytic.timesheet in load_data
                default_uom = self.pool.get('res.users').browse(cr, uid, uid).company_id.project_time_mode_id.id
                if user_related_details['product_uom_id'] != default_uom:
                    vals_line['unit_amount'] = uom_obj._compute_qty(cr, uid, default_uom, record['unit_amount'], user_related_details['product_uom_id'])
                if account_id:
                    vals_line['account_id'] = account_id
                    res = self.on_change_account_id(cr, uid, False, account_id)
                    if res.get('value'):
                        vals_line.update(res['value'])
                    vals_line['general_account_id'] = user_related_details['general_account_id']
                    vals_line['journal_id'] = user_related_details['journal_id']
                    vals_line['amount'] = 0.0
                    vals_line['product_uom_id'] = user_related_details['product_uom_id']
                else:
                    print "\n\nNo account_id found, adding it into failed record"
                    fail_records.append(current_record)
                    continue
    
                record.pop('project_id')
                if record.get('command') == 0 and not is_submitted_id:
                    context = dict(context, recompute=True)
                    print "\n\ncontext in create ::: ", context
                    timeline_id = self.create(cr, uid, vals_line, context=context) #Handle fail, if fail add into failed record
                    # Compute based on pricetype
                    amount_unit = self.on_change_unit_amount(cr, uid, timeline_id,
                        vals_line['product_id'], vals_line['unit_amount'], False, False, vals_line['journal_id'], context=context)
                    if amount_unit and 'amount' in amount_unit.get('value',{}):
                        updv = { 'amount': amount_unit['value']['amount'] }
                        self.write(cr, uid, [timeline_id], updv, context=context)
                elif record.get('command') == 1:
                    if record.get('command') != 1 and is_submitted_id:
                        id = is_submitted_id[0]
                    else:
                        id = record.get('id')
                    if 'id' in record:
                        record.pop('id')
                    line = self.browse(cr, uid, id, context=context)
                    # Compute based on pricetype
                    amount_unit = self.on_change_unit_amount(cr, uid, id,
                        prod_id=vals_line.get('product_id', line.product_id.id), company_id=False,
                        unit_amount=vals_line['unit_amount'], unit=False, journal_id=vals_line['journal_id'], context=context)
    
                    if amount_unit and 'amount' in amount_unit.get('value',{}):
                        vals_line['amount'] = amount_unit['value']['amount']
                    ctx = copy.deepcopy(context)
                    #TODO: To check, pass __last_update in context, currently it alsywas fails, that's why commented
                    #It always fails because currently our server returns __last_update value in standard datetime format without Z part
                    #ctx['__last_update'] = {("%s,%s"% (self._name,id)): record.get('__last_update')}
                    print "\n\ncontext in write ::: ", context
                    self.write(cr, uid, id, vals_line, context=ctx) #Handle fail and MissingError, if fail add into failed record
                elif record.get('command') == 2:
                    self.unlink(cr, uid, record.get('id'), context=context) #Handle fail and MissingError, if fail add into failed record

                #Replace virtual_id(project_id and task_id) in other records, so other records do not create new project and task
                if new_project_id:
                    replace_virtual_id('project_id', project_id, project_id)
                if new_task_id:
                    replace_virtual_id('task_id', task_id, task_id)
            #TODO: Handle Specific Exceptions, ValueError, AccessError, AssertError, MissingError
            except MissingError, e:
                #If record is missing we can not do anything with taht record, simply skip it
                pass
            except AccessError, e:
                current_record['fail_error'] = e
                fail_records.append(current_record)
            except ValueError, e:
                #error = (_("Value Error"), _("Please check entered values, there is something missing in values."))
                current_record['fail_error'] = e
                fail_records.append(current_record)
            except Exception, e:
                current_record['fail_error'] = (_("Error"), _("Something went wrong with  this record, make sure you have all valid values."))
                #import traceback
                #traceback.print_exc()
                #Here we can have except_orm, if there is ConcurrencyException, we will eiether simply pass or add those ids in concurrency_fail_ids because we need to re-read those records
                if isinstance(e, except_orm) and e.name == "ConcurrencyException":
                    pass
                else:
                    fail_records.append(current_record)
                cr.execute('ROLLBACK TO SAVEPOINT sync_record')
            finally:
                cr.execute('RELEASE SAVEPOINT sync_record')
        print "\n\nfail_records is ::: ", fail_records
        failed_ids = filter(lambda x: not pattern.match(str(x)), map(itemgetter('id'), fail_records))
        if failed_ids:
            load_data_domain.append(['id', 'not in', failed_ids])
        res = self.load_data(cr, uid, load_data_domain, context=context)
        res += fail_records
        result['activities'] = res
        return result

class project_timesheet_session(osv.Model):
    """
    This class meant to generate unique session_id for user, session_id is used to generate reference_id of hr.analytic.timesheet records,
    while synchronizing we will check if record with that session_id is not there, if record with that session_id is
    already there then do not create record, update the record, this basically helpful when record is sync to server
    but meanwhile server and client disconnected and when they get connected again at that time duplication doesn't occur
    """
    _name = "project.timesheet.session"

    _columns = {
        'name': fields.char('Session ID', required=True, readonly=True),
        'state': fields.selection([('opened', 'In Progress'), ('close', 'Close')], 'Status'),
        'user_id': fields.many2one('res.users', 'Responsible', required=True),
        'login_number': fields.integer("Login Number"),
        #We can add hr.analytic.timesheet as a one2many here
    }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'project.timesheet.session') or '/'
        new_id = super(project_timesheet_session, self).create(cr, uid, vals, context=context)
        return new_id
    #We will have refeence_id field in hr.analytic.timesheet, which is going to use session_id  with zero_pad same as POS
    def get_session(self, cr, uid, context=None):
        #TO Implement, this method will create new session for user which called this
        #Close the session once sync is completed or Close the session once user logout from project_timesheet interface
        #What if user already having session in In Progress, what should we return ?, if return existing session then it is quite possible that same user logs in from two system and it can create issue
        existing_session_id = self.search(cr, uid, [('user_id', '=', uid), ('state', '=', 'opened')], context=context)
        if existing_session_id:
            current_session = self.browse(cr, uid, existing_session_id[0], context=context)
            self.write(cr, uid, existing_session_id[0], {'login_number': current_session.login_number+1})
            return {'session_id': existing_session_id[0], 'login_number': current_session.login_number+1}
        session_id = self.create(cr, uid, {'user_id': uid, 'login_number': 1, 'state': 'opened'}, context=context)
        return {'session_id': session_id, 'login_number': 1}

    def close_session(self, cr, uid, session_id, context=None):
        return self.write(cr, uid, session_id, {'state': 'close'}, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
