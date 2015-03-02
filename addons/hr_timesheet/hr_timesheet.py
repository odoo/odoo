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

from openerp import models, api, fields, exceptions

from openerp.tools.translate import _

class hr_employee(models.Model):
    _inherit = "hr.employee"

    @api.model    
    # Reads the provided data file to return the default journal id for new employees    
    def _get_default_analytic_journal(self):
        return self.env.ref('hr_timesheet.analytic_journal', raise_if_not_found=False) or self.env['account.analytic.journal']

    @api.model
    # Reads the provided data file to return the default product id for new employees 
    def _get_default_employee_product(self):
        try:
            return self.env.ref('product.product_product_consultant')
        except ValueError:
            return self.env['product.product']

    product_id = fields.Many2one('product.product', 'Product', help="If you want to reinvoice working time of employees, link this employee to a service to determinate the cost price of the job.", default=_get_default_employee_product)
    journal_id = fields.Many2one('account.analytic.journal', 'Analytic Journal',default=_get_default_analytic_journal)
    uom_id =  fields.Many2one('product.uom', related='product_id.uom_id', string='Unit of Measure', store=True, readonly=True)

# At the moment, we assume that a user is related to only one employee, and if not we still only select the first employee record related to this user. 
class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'

    # def create(self, cr, uid, vals, context=None):
    #     return super(account_analytic_line, self).create(self, cr, uid, vals, context=context)


    def default_get(self,cr,uid,fields,context=None):
        values = super(account_analytic_line, self).default_get(cr, uid, fields, context=context)
        #####################################################################################################
        ## Small Fix to allow creation of timesheets from the project_timesheet UI. Might be removed later ##
        #####################################################################################################
        if context.get('default_is_timesheet'):
            values['is_timesheet'] =  True
        ##########################################
        if values.get('is_timesheet'):
            if 'product_uom_id' in fields:
                values['product_uom_id'] = self._get_employee_unit(cr, uid, context=context)
            if 'product_id' in fields:    
                values['product_id'] = self._get_employee_product(cr, uid, context=context)
            if 'general_account_id' in fields:    
                values['general_account_id'] = self._get_general_account(cr, uid, context=context)
            if 'journal_id' in fields:    
                values['journal_id'] = self._get_analytic_journal(cr, uid, context=context)
        return values

    #This method is used by some modules having dependencies on this one.
    def on_change_unit_amount_2(self, cr, uid, id, prod_id, unit_amount, company_id, unit=False, journal_id=False, context=None):
        res = {'value':{}}

        if not prod_id:
            emp_obj = self.pool.get('hr.employee')
            emp_id = emp_obj.search(cr, uid, [('user_id', '=', uid)], context=context)
            if emp_id:
                emp = emp_obj.browse(cr, uid, emp_id[0], context=context)
                if emp.product_id:
                    prod_id =  emp.product_id.id

        if prod_id and unit_amount:
            # find company
            company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', context=context)
            r = self.on_change_unit_amount(cr, uid, id, prod_id, unit_amount, company_id, unit, journal_id, context=context)
            if r:
                res.update(r)
        # update unit of measurement
        if prod_id:
            uom = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
            if uom.uom_id:
                res['value'].update({'product_uom_id': uom.uom_id.id})
            else:
                res['value'].update({'product_uom_id': False})
                return res
        return res

    @api.model
    def _get_employee_product(self, user_id=None):
        emp = self.env['hr.employee'].search([('user_id', '=', self.user_id.id or user_id  or self.env.uid)])
        if emp and emp[0].product_id.id:
            return emp[0].product_id.id
        else:
            raise exceptions.ValidationError("This user or employee is not associated to a valid Product")
    @api.model
    def _get_employee_unit(self, user_id=None):
            emp = self.env['hr.employee'].search([('user_id', '=', self.user_id.id or user_id or self.env.uid)])
            if emp and emp[0].product_id.uom_id.id:
                return emp[0].product_id.uom_id.id
            else:
                raise exceptions.ValidationError("This user or employee is not associated to a valid Product Amount Type")    

    @api.model
    def _get_general_account(self, user_id=None):
        emp = self.env['hr.employee'].search([('user_id', '=', self.user_id.id or user_id or self.env.uid)])
        if emp and emp[0].product_id.categ_id.property_account_expense_categ.id:
            return emp[0].product_id.categ_id.property_account_expense_categ.id
        else:
            raise exceptions.ValidationError("This user or employee is not associated to a valid Product Financial Account")

    @api.model
    def _get_analytic_journal(self, user_id=None):
        emp = self.env['hr.employee'].search([('user_id','=',self.user_id.id or user_id or self.env.uid)])
        if emp and emp[0].journal_id.id:
            return emp[0].journal_id.id
        else:
            raise exceptions.ValidationError("This user or employee is not associated to a valid Journal ID")

    is_timesheet = fields.Boolean()
   
    @api.constrains('user_id')
    def check_user_id(self):
        if self.is_timesheet:
            emp = self.env['hr.employee'].search([('user_id','=',self.user_id.id or self.env.uid)])
            if not emp:
                raise exceptions.ValidationError("There is no employee defined for user " + self.user_id.name)
            else:
                if not emp[0].journal_id.id:
                    raise exceptions.ValidationError("The employee " + emp[0].name + " is not associated to a valid Analytic Journal. Please define one for him or select another user.")
                elif not emp[0].product_id:
                    raise exceptions.ValidationError("The employee " + emp[0].name + " is not associated to a valid Product. Please define one for him or select another user.")
                elif not emp[0].product_id.uom_id.id:
                    raise exceptions.ValidationError("The employee " + emp[0].name + " is not associated to a valid Product Unit of Measure. Please define one for him or select another user.")
                elif not emp[0].product_id.categ_id.property_account_expense_categ.id:
                    raise exceptions.ValidationError("The employee " + emp[0].name + " is not associated to a valid Financial Account. Please define one for him or select another user.")

    @api.onchange('user_id')
    def V8_on_change_user_id(self):
        if self.is_timesheet:
            new_values = self.on_change_user_id(self.user_id.id, self.is_timesheet)
            self.journal_id = new_values["value"]['journal_id']
            self.product_id = new_values["value"]['product_id']
            self.product_uom_id = new_values["value"]['uom_id']
            self.general_account_id = new_values["value"]['general_account_id']

            # New API style
            #     emp = self.env['hr.employee'].search([('user_id','=',self.user_id.id or self.env.uid)])
            #     if not emp:
            #         model, action_id = self.env['ir.model.data'].get_object_reference('hr', 'open_view_employee_list_my')
            #         msg = _("Employee is not created for this user. Please create one from configuration panel.")
            #         raise exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            #     else:
            #         self.journal_id = self._get_analytic_journal()
            #         self.product_id = self._get_employee_product()
            #         self.product_uom_id = self._get_employee_unit()
            #         self.general_account_id = self._get_general_account()

    def on_change_user_id(self, cr, uid, ids, user_id, is_timesheet=False, context=None):
        if is_timesheet:
            if not user_id:
                return {}
            else:
                res = {"value": {
                    'journal_id' : self._get_analytic_journal(cr,uid, user_id, context=context),
                    'product_id' : self._get_employee_product(cr,uid, user_id, context=context),
                    'uom_id' : self._get_employee_unit(cr,uid, user_id, context=context),
                    'general_account_id' : self._get_general_account(cr,uid, user_id, context=context)
                    }
                }
                return res

    @api.onchange('date')
    def on_change_date(self):
        if self.is_timesheet:
            if self._origin.date and (self._origin.date != self.date):
                raise exceptions.Warning('Changing the date will let this entry appear in the timesheet of the new date.')

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'

    use_timesheets = fields.Boolean('Timesheets', help="Check this field if this project manages timesheets", deprecated=True)
    invoice_on_timesheets = fields.Boolean('Timesheets', help="Check this field if this project manages timesheets")

    @api.onchange('invoice_on_timesheets')
    def onchange_invoice_on_timesheets(self):
        result = {}
        if not self.invoice_on_timesheets:
            return {'value': {'to_invoice': False}}
        try:
            to_invoice = self.env['ir.model.data'].xmlid_to_res_id('hr_timesheet_invoice.timesheet_invoice_factor1')
            result['to_invoice'] = to_invoice
        except ValueError:
            pass
        return result

    #TODO: 
    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['invoice_on_timesheets'] = template.invoice_on_timesheets
        return res

