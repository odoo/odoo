#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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

import time
import netsvc
from osv import osv
from osv import fields
from tools import config
from tools.translate import _

from datetime import date
from datetime import datetime
from datetime import timedelta

def prev_bounds(cdate=False):
    when = date.fromtimestamp(time.mktime(time.strptime(cdate,"%Y-%m-%d")))
    this_first = date(when.year, when.month, 1)
    month = when.month + 1
    year = when.year
    if month > 12:
        month = 1
        year += 1
    next_month = date(year, month, 1)
    prev_end = next_month - timedelta(days=1)
    return this_first, prev_end

class hr_contract_wage_type(osv.osv):
    """
    Wage types
    Basic = Basic Salary
    Grows = Basic + Allowances
    New = Grows - Deductions
    """
    
    _inherit = 'hr.contract.wage.type'
    _columns = {
        'type' : fields.selection([('basic','Basic'), ('gross','Gross'), ('net','Net')], 'Type', required=True),
    }
hr_contract_wage_type()

class hr_passport(osv.osv):
    """
    Employee Passport
    Passport based Contratacts for Employees
    """
    
    _name = 'hr.passport'
    _description = 'Passport Detail'
    
    _columns = {
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'name':fields.char('Passport No', size=64, required=True, readonly=False),
        'country_id':fields.many2one('res.country', 'Country of Issue', required=True),
        'address_id':fields.many2one('res.partner.address', 'Address', required=False),
        'date_issue': fields.date('Passport Issue Date', required=True),
        'date_expire': fields.date('Passport Expire Date', required=True),
        'contracts_ids':fields.one2many('hr.contract', 'passport_id', 'Contracts', required=False, readonly=True),
        'note': fields.text('Description'),
    }
hr_passport()

class hr_payroll_structure(osv.osv):
    """
    Salary structure used to defined
    - Basic
    - Allowlance
    - Deductions
    """
    
    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'

    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, readonly=False),
        'line_ids':fields.one2many('hr.payslip.line', 'function_id', 'Salary Structure', required=False),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', required=False),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'note': fields.text('Description'),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
    
    def copy(self, cr, uid, id, default=None, context=None):
        """
        Create a new record in hr_payroll_structure model from existing one
        @param cr: cursor to database
        @param user: id of current user
        @param id: list of record ids on which copy method executes
        @param default: dict type contains the values to be override during copy of object
        @param context: context arguments, like lang, time zone
        
        @return: returns a id of newly created record
        """
        code = self.browse(cr, uid, id).code
        default = {
            'code':code+"(copy)",
            'company_id':self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        }
        res_id = super(hr_payroll_structure, self).copy(cr, uid, id, default, context)
        return res_id
    
hr_payroll_structure()

class hr_contract(osv.osv):
    """
    Employee contract based on the visa, work permits
    allowas to configure different Salary structure
    """
    
    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    
    _columns = {
        'permit_no':fields.char('Work Permit No', size=256, required=False, readonly=False),
        'passport_id':fields.many2one('hr.passport', 'Passport', required=False),
        'visa_no':fields.char('Visa No', size=64, required=False, readonly=False),
        'visa_expire': fields.date('Visa Expire Date'),
        'struct_id' : fields.many2one('hr.payroll.structure', 'Salary Structure'),
        'working_days_per_week': fields.integer('Working Days', help="No of Working days / week for an employee")
    }
    _defaults = {
        'working_days_per_week': lambda *a: 5,
    }
hr_contract()

class payroll_register(osv.osv):
    """
    Payroll Register
    """
    _name = 'hr.payroll.register'
    _description = 'Payroll Register'
    
    def _calculate(self, cr, uid, ids, field_names, arg, context):
        res = {}
        allounce = 0.0
        deduction = 0.0
        net = 0.0
        grows = 0.0
        for register in self.browse(cr, uid, ids, context):
            for slip in register.line_ids:
                allounce += slip.allounce
                deduction += slip.deduction
                net += slip.net
                grows += slip.grows
                
            res[register.id] = {
                'allounce':allounce,
                'deduction':deduction,
                'net':net,
                'grows':grows
            }
        return res
        
    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'date': fields.date('Date', required=True),
        'number':fields.char('Number', size=64, required=False, readonly=True),
        'line_ids':fields.one2many('hr.payslip', 'register_id', 'Payslips', required=False),
        'state':fields.selection([
            ('new','New Slip'),
            ('draft','Wating for Verification'),
            ('hr_check','Wating for HR Verification'),
            ('accont_check','Wating for Account Verification'),
            ('confirm','Confirm Sheet'),
            ('done','Paid Salary'),
            ('cancel','Reject'),
        ],'State', select=True, readonly=True),
        'journal_id': fields.many2one('account.journal', 'Expanse Journal', required=True),
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal', required=True),
        'active':fields.boolean('Active', required=False),
#        'advice_ids':fields.one2many('hr.payroll.advice', 'register_id', 'Bank Advice'),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], help="Keep empty to use the period of the validation(Payslip) date."),
        'grows': fields.function(_calculate, method=True, store=True, multi='dc', string='Gross Salary', type='float', digits=(16, int(config['price_accuracy']))),
        'net': fields.function(_calculate, method=True, store=True, multi='dc', string='Net Salary', digits=(16, int(config['price_accuracy']))),
        'allounce': fields.function(_calculate, method=True, store=True, multi='dc', string='Allowance', digits=(16, int(config['price_accuracy']))),
        'deduction': fields.function(_calculate, method=True, store=True, multi='dc', string='Deduction', digits=(16, int(config['price_accuracy']))),        
        'note': fields.text('Description'),
    }
    
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'new',
        'active': lambda *a: True,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }

    def compute_sheet(self, cr, uid, ids, context={}):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        wf_service = netsvc.LocalService("workflow")
        
        vals = self.browse(cr, uid, ids)[0]
        
        emp_ids = emp_pool.search(cr, uid, [])
        
        for emp in emp_pool.browse(cr, uid, emp_ids):
            old_slips = slip_pool.search(cr, uid, [('employee_id','=',emp.id), ('date','=',vals.date)])
            if old_slips:
                slip_pool.write(cr, uid, old_slips, {'register_id':ids[0]})
                for sid in old_slips:
                    wf_service.trg_validate(uid, 'hr.payslip', sid, 'compute_sheet', cr)
                continue
                
            res = {
                'employee_id':emp.id,
                'register_id':ids[0],
                'name':vals.name,
                'date':vals.date,
                'journal_id':vals.journal_id.id,
                'bank_journal_id':vals.bank_journal_id.id
            }
            slip_id = slip_pool.create(cr, uid, res)
            wf_service.trg_validate(uid, 'hr.payslip', slip_id, 'compute_sheet', cr)
        
        number = self.pool.get('ir.sequence').get(cr, uid, 'salary.register')
        self.write(cr, uid, ids, {'state':'draft', 'number':number})
        return True

    def verify_sheet(self, cr, uid, ids, context={}):
        slip_pool = self.pool.get('hr.payslip')
        
        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id)])
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'verify_sheet', cr)
        
        self.write(cr, uid, ids, {'state':'hr_check'})
        return True
    
    def verify_twice_sheet(self, cr, uid, ids, context={}):
        slip_pool = self.pool.get('hr.payslip')
        
        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id), ('state','=','hr_check')])
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'verify_twice_sheet', cr)
        
        self.write(cr, uid, ids, {'state':'accont_check'})
        return True
    
    def final_verify_sheet(self, cr, uid, ids, context={}):
        slip_pool = self.pool.get('hr.payslip')
        advice_pool = self.pool.get('hr.payroll.advice')
        advice_line_pool = self.pool.get('hr.payroll.advice.line')
        
        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id), ('state','=','accont_check')])
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'final_verify_sheet', cr)

        for reg in self.browse(cr, uid, ids):
            accs = {}
            for slip in reg.line_ids:
                pid = False
                if accs.get(slip.employee_id.property_bank_account.code, False) == False:
                    company_name = self.pool.get('res.users').browse(cr, uid, uid).company_id.name
                    bank_name = slip.employee_id.property_bank_account.name
                    number = self.pool.get('ir.sequence').get(cr, uid, 'payment.advice')
                    advice = {
                        'name': 'Payment Advice from %s / Bank Account %s' % (company_name, bank_name),
                        'number': number,
                        'register_id':reg.id,
                        'account_id':slip.employee_id.property_bank_account.id
                    }
                    pid = advice_pool.create(cr, uid, advice)
                    accs[slip.employee_id.property_bank_account.code] = pid
                else:
                    pid = accs[slip.employee_id.property_bank_account.code]
                
                if not slip.employee_id.bank_account_id:
                    raise osv.except_osv(_('Warning'), _("Bank Account not defined for %s !" % (slip.employee_id.name)))
                else:
                    pline = {
                        'advice_id':pid,
                        'name':slip.employee_id.bank_account_id.acc_number,
                        'employee_id':slip.employee_id.id,
                        'amount':slip.other_pay + slip.net,
                        'bysal':slip.net
                    }
                    id = advice_line_pool.create(cr, uid, pline)
        
        self.write(cr, uid, ids, {'state':'confirm'})
        return True

    def process_sheet(self, cr, uid, ids, context={}):
        slip_pool = self.pool.get('hr.payslip')
        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id), ('state','=','confirm')])
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'process_sheet', cr)
        
        self.write(cr, uid, ids, {'state':'done'})
        return True

payroll_register()

class payroll_advice(osv.osv):
    '''
    Bank Advice Note
    '''
    _name = 'hr.payroll.advice'
    _description = 'Bank Advice Note'
    
    _columns = {
        'register_id':fields.many2one('hr.payroll.register', 'Payroll Register', required=False),
        'name':fields.char('Name', size=2048, required=True, readonly=False),
        'note': fields.text('Description'),
        'date': fields.date('Date'),
        'state':fields.selection([
            ('draft','Draft Sheet'),
            ('confirm','Confirm Sheet'),
            ('cancel','Reject'),
        ],'State', select=True, readonly=True),
        'number':fields.char('Number', size=64, required=False, readonly=True),
        'line_ids':fields.one2many('hr.payroll.advice.line', 'advice_id', 'Employee Salary', required=False),
        'chaque_nos':fields.char('Chaque Nos', size=256, required=False, readonly=False),
        'account_id': fields.many2one('account.account', 'Account', required=True),
        'company_id':fields.many2one('res.company', 'Company', required=False),
    }
    
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'draft',
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
    
    def confirm_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'confirm'})
        return True
        
    def set_to_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def cancel_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'cancel'})
        return True

payroll_advice()

class payroll_advice_line(osv.osv):
    '''
    Bank Advice Lines
    '''
    _name = 'hr.payroll.advice.line'
    _description = 'Bank Advice Lines'
    
    _columns = {
        'advice_id':fields.many2one('hr.payroll.advice', 'Bank Advice', required=False),
        'name':fields.char('Bank Account A/C', size=64, required=True, readonly=False),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'amount': fields.float('Amount', digits=(16, int(config['price_accuracy']))),
        'bysal': fields.float('By Salary', digits=(16, int(config['price_accuracy']))),
        'flag':fields.char('D/C', size=8, required=True, readonly=False),
    }
    _defaults = {
        'flag': lambda *a: 'C',
    }
    
    def onchange_employee_id(self, cr, uid, ids, ddate, employee_id, context={}):
        vals = {}
        slip_pool = self.pool.get('hr.payslip')        
        if employee_id:
            dates = prev_bounds(ddate)
            sids = False
            sids = slip_pool.search(cr, uid, [('paid','=',False),('state','=','confirm'),('date','>=',dates[0]), ('employee_id','=',employee_id), ('date','<=',dates[1])])
            if sids:
                slip = slip_pool.browse(cr, uid, sids[0])
                vals['name'] = slip.employee_id.otherid
                vals['amount'] = slip.net + slip.other_pay
                vals['bysal'] = slip.net
        return {
            'value':vals
        }
payroll_advice_line()

class contrib_register(osv.osv):
    '''
    Contribution Register
    '''
    _name = 'hr.contibution.register'
    _description = 'Contribution Register'
    
    def _total_contrib(self, cr, uid, ids, field_names, arg, context={}):
        line_pool = self.pool.get('hr.contibution.register.line')
        period_id = self.pool.get('account.period').search(cr,uid,[('date_start','<=',time.strftime('%Y-%m-%d')),('date_stop','>=',time.strftime('%Y-%m-%d'))])[0]
        fiscalyear_id = self.pool.get('account.period').browse(cr, uid, period_id).fiscalyear_id
        res = {}
        for cur in self.browse(cr, uid, ids):
            current = line_pool.search(cr, uid, [('period_id','=',period_id),('register_id','=',cur.id)])
            years = line_pool.search(cr, uid, [('period_id.fiscalyear_id','=',fiscalyear_id.id), ('register_id','=',cur.id)])
        
            e_month = 0.0
            c_month = 0.0
            for i in line_pool.browse(cr, uid, current):
                e_month += i.emp_deduction
                c_month += i.comp_deduction
            
            e_year = 0.0
            c_year = 0.0
            for j in line_pool.browse(cr, uid, years):
                e_year += i.emp_deduction
                c_year += i.comp_deduction
                
            res[cur.id]={
                'monthly_total_by_emp':e_month,
                'monthly_total_by_comp':c_month,
                'yearly_total_by_emp':e_year,
                'yearly_total_by_comp':c_year
            }
            
        return res

    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'account_id': fields.many2one('account.account', 'Account', required=True),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'register_line_ids':fields.one2many('hr.contibution.register.line', 'register_id', 'Register Line', readonly=True),
        'yearly_total_by_emp': fields.function(_total_contrib, method=True, multi='dc', store=True, string='Total By Employee', digits=(16, int(config['price_accuracy']))),
        'yearly_total_by_comp': fields.function(_total_contrib, method=True, multi='dc', store=True,  string='Total By Company', digits=(16, int(config['price_accuracy']))),
        'monthly_total_by_emp': fields.function(_total_contrib, method=True, multi='dc', store=True, string='Total By Employee', digits=(16, int(config['price_accuracy']))),
        'monthly_total_by_comp': fields.function(_total_contrib, method=True, multi='dc', store=True,  string='Total By Company', digits=(16, int(config['price_accuracy']))),        
        'note': fields.text('Description'),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
contrib_register()

class contrib_register_line(osv.osv):
    '''
    Contribution Register Line
    '''
    _name = 'hr.contibution.register.line'
    _description = 'Contribution Register Line'
  
    def _total(self, cr, uid, ids, field_names, arg, context):
        res={}
        for line in self.browse(cr, uid, ids, context):
            res[line.id] = line.emp_deduction + line.comp_deduction
            return res
    
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'register_id':fields.many2one('hr.contibution.register', 'Register', required=False),
        'code':fields.char('Code', size=64, required=False, readonly=False),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'period_id': fields.many2one('account.period', 'Period'),
        'emp_deduction': fields.float('Employee Deduction', digits=(16, int(config['price_accuracy']))),
        'comp_deduction': fields.float('Company Deduction', digits=(16, int(config['price_accuracy']))),
        'total': fields.function(_total, method=True, store=True,  string='Total', digits=(16, int(config['price_accuracy']))),    
    }
contrib_register_line()

class payment_category(osv.osv):
    """
    Allowance, Deduction Heads
    House Rent Allowance, Medical Allowance, Food Allowance
    Professional Tax, Advance TDS, Providend Funds, etc    
    """
    
    _name = 'hr.allounce.deduction.categoty'
    _description = 'Allowance Deduction Heads'
    
    _columns = {
        'name':fields.char('Categoty Name', size=64, required=True, readonly=False),
        'code':fields.char('Categoty Code', size=64, required=True, readonly=False),
        'type':fields.selection([
            ('allowance','Allowance'),
            ('deduction','Deduction'),
            ('other','Others'),
        ],'Type', select=True),
        'base': fields.text('Based on', required=True, readonly=False, help='This will use to computer the % fields values, in general its on basic, but You can use all heads code field in small letter as a variable name i.e. hra, ma, lta, etc...., also you can use, static varible basic'),
        #'base':fields.char('Based on', size=64, required=True, readonly=False, help='This will use to computer the % fields values, in general its on basic, but You can use all heads code field in small letter as a variable name i.e. hra, ma, lta, etc...., also you can use, static varible basic'),
        'condition':fields.char('Condition', size=1024, required=True, readonly=False, help='Applied this head for calculation if condition is true'),
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence'),
        'note': fields.text('Description'),    
        'user_id':fields.char('User', size=64, required=False, readonly=False),
        'state':fields.char('Label', size=64, required=False, readonly=False),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'contribute_ids':fields.one2many('company.contribution', 'category_id', 'Company Contribution', required=False),
    }
    _defaults = {
        'condition': lambda *a: 'True',
        'base': lambda *a:'basic',
        'sequence': lambda *a:5,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
payment_category()

class company_contribution(osv.osv):
    """
    Company contribution
    Allows to configure company contribution for some taxes
    """
    
    _name = 'company.contribution'
    _description = "Company Contribution"
    
    _columns = {
        'category_id':fields.many2one('hr.allounce.deduction.categoty', 'Heads', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, readonly=False),
        'include_in_salary':fields.boolean('Included in Salary ?', help='If company contribute on this deduction then should company contribution is also deducted from Employee Salary'),
        'gratuity':fields.boolean('Use for Gratuity ?', required=False),
        'line_ids':fields.one2many('company.contribution.line', 'contribution_id', 'Calculations', required=False),
        'register_id':fields.property(
            'hr.contibution.register',
            type='many2one',
            relation='hr.contibution.register',
            string="Contribution Register",
            method=True,
            view_load=True,
            help="Contribution register based on company",
            required=False
        ),
        'amount_type':fields.selection([
            ('fix','Fixed Amount'),
            ('func','Function Calculation'),
        ],'Amount Type', select=True),
        'contribute_per':fields.float('Contribution', digits=(16, int(config['price_accuracy'])), help='Define Company contribution ratio 1.00=100% contribution, If Employee Contribute 5% then company will and here 0.50 defined then company will contribute 50% on employee 5% contribution'),
        'account_id':fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Account",
            method=True,
            view_load=True,
            help="Expanse account where company expanse will be encoded",
            required=False
        ),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'active':fields.boolean('Active', required=False),
        'note': fields.text('Description'),
    }
    
    _defaults = {
        'amount_type': lambda *a:'fix',
        'active': lambda *a:True,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
    
    def execute_function(self, cr, uid, id, value, context):
        """
        self: pointer to self object
        cr: cursor to database
        uid: user id of current executer
        """
        
        line_pool = self.pool.get('company.contribution.line')
        res = 0
        ids = line_pool.search(cr, uid, [('category_id','=',id), ('to_val','>=',value),('from_val','<=',value)])
        if not ids:
            ids = line_pool.search(cr, uid, [('category_id','=',id), ('from','<=',value)])
        if not ids:
            res = 0
        else:
            res = line_pool.browse(cr, uid, ids)[0].value
        return res
    
company_contribution()

class company_contribution_line(osv.osv):
    """
    Company contribution lines
    """
    
    _name = 'company.contribution.line'
    _description = 'Allowance Deduction Categoty'
    _order = 'sequence'
    
    _columns = {
        'contribution_id':fields.many2one('company.contribution', 'Contribution', required=False),
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'umo_id':fields.many2one('product.uom', 'Unite', required=False),
        'from_val': fields.float('From', digits=(16, int(config['price_accuracy']))),
        'to_val': fields.float('To', digits=(16, int(config['price_accuracy']))),
        'amount_type':fields.selection([
            ('fix','Fixed Amount'),
        ],'Amount Type', select=True),
        'sequence':fields.integer('Sequence'),
        'value': fields.float('Value', digits=(16, int(config['price_accuracy']))),
    }
company_contribution_line()

class hr_holidays_status(osv.osv):
    _inherit = "hr.holidays.status"
    
    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'type':fields.selection([
            ('paid','Paid Holiday'), 
            ('unpaid','Un-Paid Holiday'), 
            ('halfpaid','Half-Pay Holiday')
            ], string='Payment'),
        'account_id': fields.many2one('account.account', 'Account', required=False),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account', required=False),
        'head_id': fields.many2one('hr.allounce.deduction.categoty', 'Payroll Head', domain=[('type','=','deduction')]),
        'code':fields.char('Code', size=64, required=False, readonly=False),
    }
    _defaults = {
        'type': lambda *args: 'unpaid',
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
hr_holidays_status()

class hr_expense_expense(osv.osv):
    _inherit = "hr.expense.expense"
    _description = "Expense"
    _columns = {
        'category_id':fields.many2one('hr.allounce.deduction.categoty', 'Payroll Head', domain=[('type','=','other')]),
    }
hr_expense_expense()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    
    def _calculate(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for rs in self.browse(cr, uid, ids, context):
            allow = 0.0
            deduct = 0.0
            others = 0.0
            
            obj = {
                'basic':rs.basic
            }
            if rs.igross > 0:
                obj.update({
                    'gross':rs.igross
                })
            if rs.inet > 0:
                obj.update({
                    'net':rs.inet
                })
            
            for line in rs.line_ids:
                amount = 0.0
                
                if line.amount_type == 'per':
                    try:
                        amount = line.amount * eval(str(line.category_id.base), obj)
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error : %s ' % (e)))
                    
                elif line.amount_type in ('fix', 'func'):
                    amount = line.amount

                cd = line.category_id.code.lower()
                obj[cd] = amount
                
                contrib = 0.0
#                if line.category_id.include_in_salary:
#                    contrib = line.company_contrib

                if line.type == 'allowance':
                    allow += amount
                    others += contrib
                    amount -= contrib
                elif line.type == 'deduction':
                    deduct += amount
                    others -= contrib
                    amount += contrib
                elif line.type == 'advance':
                    others += amount
                elif line.type == 'loan':
                    others += amount
                elif line.type == 'otherpay':
                    others += amount
                
                self.pool.get('hr.payslip.line').write(cr, uid, [line.id], {'total':amount})
                
            record = {
                'allounce':round(allow),
                'deduction':round(deduct),
                'grows':round(rs.basic + allow),
                'net':round(rs.basic + allow - deduct),
                'other_pay':others,
                'total_pay':round(rs.basic + allow - deduct)
            }
            res[rs.id] = record
        
        return res
    
    _columns = {
        'deg_id':fields.many2one('hr.payroll.structure', 'Designation', required=False),
        'register_id':fields.many2one('hr.payroll.register', 'Register', required=False),
        'journal_id': fields.many2one('account.journal', 'Expanse Journal', required=True),
        'bank_journal_id': fields.many2one('account.journal', 'Bank Journal', required=True),
        'name':fields.char('Name', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'number':fields.char('Number', size=64, required=False, readonly=True),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'date': fields.date('Date'),
        'state':fields.selection([
            ('new','New Slip'),
            ('draft','Wating for Verification'),
            ('hr_check','Wating for HR Verification'),
            ('accont_check','Wating for Account Verification'),
            ('confirm','Confirm Sheet'),
            ('done','Paid Salary'),
            ('cancel','Reject'),
        ],'State', select=True, readonly=True),
        'basic_before_leaves': fields.float('Basic Salary', readonly=True,  digits=(16, 2)),
        'leaves': fields.float('Leaved Deduction', readonly=True,  digits=(16, 2)),
        'basic': fields.float('Basic Salary - Leaves', readonly=True,  digits=(16, 2)),
        'grows': fields.function(_calculate, method=True, store=True, multi='dc', string='Gross Salary', type='float', digits=(16, 2)),
        'net': fields.function(_calculate, method=True, store=True, multi='dc', string='Net Salary', digits=(16, 2)),
        'allounce': fields.function(_calculate, method=True, store=True, multi='dc', string='Allowance', digits=(16, 2)),
        'deduction': fields.function(_calculate, method=True, store=True, multi='dc', string='Deduction', digits=(16, 2)),
        'other_pay': fields.function(_calculate, method=True, store=True, multi='dc', string='Others', digits=(16, 2)),
        'total_pay': fields.function(_calculate, method=True, store=True, multi='dc', string='Total Payment', digits=(16, 2)),
        'line_ids':fields.one2many('hr.payslip.line', 'slip_id', 'Payslip Line', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'holiday_days': fields.integer('No of Leaves', readonly=True),
        'worked_days': fields.integer('Worked Day', readonly=True),
        'working_days': fields.integer('Working Days', readonly=True),
        'paid':fields.boolean('Paid ? ', required=False),
        'note':fields.text('Description'),
        'contract_id':fields.many2one('hr.contract', 'Contract', required=False),
        
        'igross': fields.float('Calculaton Field', readonly=True,  digits=(16, 2), help="Calculation field used for internal calculation, do not place this on form"),
        'inet': fields.float('Calculaton Field', readonly=True,  digits=(16, 2), help="Calculation field used for internal calculation, do not place this on form"),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': lambda *a: 'new',
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }
    
    def copy(self, cr, uid, id, default=None, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        default = {
            'line_ids': False,
            'move_ids': False,
            'move_line_ids': False,
            'move_payment_ids': False,
            'company_id':company_id,
            'period_id': False,
            'basic_before_leaves':0,
            'basic':0
        }
        res_id = super(hr_payslip, self).copy(cr, uid, id, default, context)
        return res_id
    
    def set_to_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'})
        return True
    
    def cancel_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
    def process_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done'})
        return True
    
    def account_check_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'accont_check'})
        return True
    
    def hr_check_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'hr_check'})
        return True
    
    def verify_sheet(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'confirm'})
        return True
    
    def get_contract(self, cr, uid, employee, date, context={}):
        """
        Compute leaves for an employee
        
        @param cr: cursor to database
        @param uid: id of current user
        @param employee: object of the hr.employee model
        @param date: date on which pay slip is creating
        @param context: context arguments, like lang, time zone
        
        @return: return a current contract from the list of contract
        """
        
        sql_req= '''
            SELECT c.id as id, c.wage as wage, struct_id as function
            FROM hr_contract c
              LEFT JOIN hr_employee emp on (c.employee_id=emp.id)
              LEFT JOIN hr_contract_wage_type cwt on (cwt.id = c.wage_type_id)
              LEFT JOIN hr_contract_wage_type_period p on (cwt.period_id = p.id)
            WHERE
              (emp.id=%s) AND
              (date_start <= %s) AND
              (date_end IS NULL OR date_end >= %s)
            LIMIT 1
            '''
        cr.execute(sql_req, (employee.id, date, date))
        contract = cr.dictfetchone()
        
        return contract
    
    def _get_leaves(self, cr, user, slip, employee, context={}):
        """
        Compute leaves for an employee
        
        @param cr: cursor to database
        @param user: id of current user
        @param slip: object of the hr.payroll.slip model
        @param employee: object of the hr.employee model
        @param context: context arguments, like lang, time zone
        @return: return a result
        """
        
        result = []

        dates = prev_bounds(slip.date)
        sql = '''select id from hr_holidays
                    where date_from >= '%s' and date_to <= '%s' 
                    and employee_id = %s 
                    and state = 'validate' ''' % (dates[0], dates[1], slip.employee_id.id)
        cr.execute(sql)
        res = cr.fetchall()

        if res:
            result = [x[0] for x in res]
        
        return result
        
    def compute_sheet(self, cr, uid, ids, context={}):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        func_pool = self.pool.get('hr.payroll.structure')
        slip_line_pool = self.pool.get('hr.payslip.line')
        holiday_pool = self.pool.get('hr.holidays')
        
        date = self.read(cr, uid, ids, ['date'])[0]['date']
        
        #Check for the Holidays
        def get_days(start, end, month, year, calc_day):
            count = 0
            import datetime
            for day in range(start, end):
                if datetime.date(year, month, day).weekday() == calc_day:
                    count += 1
            return count

        basic = 0.0
        contract = False
        for slip in self.browse(cr, uid, ids):
            basic = 0.0
            
            contracts = self.get_contract(cr, uid, slip.employee_id, date, context)
            
            if not contracts or contracts.get('id', False) == False:
                continue
                
            
            contract = self.pool.get('hr.contract').browse(cr, uid, contracts.get('id'))
            sal_type = contract.wage_type_id.type
            function = contract.struct_id.id
            
            lines = []
            if function:
                func = func_pool.read(cr, uid, function, ['line_ids'])
                lines = slip_line_pool.browse(cr, uid, func['line_ids'])
            
            lines += slip.employee_id.line_ids
            
            old_slip_id = slip_line_pool.search(cr, uid, [('slip_id','=',slip.id)])
            slip_line_pool.unlink(cr, uid, old_slip_id)
            
            ad = []
            lns = {}
            all_per = 0.0
            ded_per = 0.0
            all_fix = 0.0
            ded_fix = 0.0
            
            obj = {
                'basic':0.0
            }
            update = {
            
            }
            
            if contract.wage_type_id.type == 'gross':
                obj['gross'] = contract.wage
                update['igross'] = contract.wage
            if contract.wage_type_id.type == 'net':
                obj['net'] = contract.wage
                update['inet'] = contract.wage
            if contract.wage_type_id.type == 'basic':
                obj['basic'] = contract.wage
                update['basic'] = contract.wage
            
            c_type = {
            
            }

            for line in lines:
                cd = line.code.lower()
                obj[cd] = line.amount or 0.0
            
            for line in lines:
            
                if line.category_id.code in ad:
                    continue
                    
                ad.append(line.category_id.code)
                cd = line.category_id.code.lower()
                
                calculate = False
                try:
                    exp = line.category_id.condition
                    calculate = eval(exp, obj)
                except Exception, e:
                    raise osv.except_osv(_('Variable Error !'), _('Variable Error : %s ' % (e)))

                if not calculate:
                    continue
                
                percent = 0.0
                value = 0.0
                base = False
                company_contrib = 0.0
                base = line.category_id.base
                
                try:
                    # Please have a look at the configuration guide for rules and restrictions
                    amt = eval(base, obj)
                except Exception, e:
                    raise osv.except_osv(_('Variable Error !'), _('Variable Error : %s ' % (e)))

                if sal_type in ('gross', 'net'):
                    if line.amount_type == 'per':
                        percent = line.amount
                        
                        if amt > 1:
                            value = percent * amt
                        elif amt > 0 and amt <= 1:
                            percent = percent * amt
                        
                        if value > 0:
                            percent = 0.0

                        for cline in line.category_id.contribute_ids:
                            pass
                        
                    elif line.amount_type == 'fix':
                        value = line.amount
                    
                    elif line.amount_type == 'func':
                        value = self.pool.get('hr.payslip.line').execute_function(cr, uid, line.id, amt, context)
                        line.amount = value
                else:
                    if line.amount_type == 'func':
                        value = self.pool.get('hr.payslip.line').execute_function(cr, uid, line.id, amt, context)
                        line.amount = value
                    
#                    for cline in line.category_id.contribute_ids:
#                        if cline.amount_type == 'fix':
#                            contribute = cline.contribute_per
#                        elif cline.amount_type == 'func':
#                            contribute = func_pool.execute_function(cr, uid, cline.id, line.amount, context)
                    
                if line.type == 'allowance':
                    all_per += percent
                    all_fix += value
                elif line.type == 'deduction':
                    ded_per += percent
                    ded_fix += value
                
                vals = {
                    'amount':line.amount, 
                    'slip_id':slip.id, 
                    'employee_id':False, 
                    'function_id':False,
                    'base':base
                }
                slip_line_pool.copy(cr, uid, line.id, vals, {})
            
            if sal_type in ('gross', 'net'):
                sal = contract.wage
                if sal_type == 'net':
                    sal += ded_fix
                sal -= all_fix
                per = 0.0
                if sal_type == 'net':
                    per = (all_per - ded_per)
                else:
                    per = all_per
                if per <=0 :
                    per *= -1
                final = (per * 100) + 100
                basic = (sal * 100) / final
            else:
                basic = contract.wage
            
            number = self.pool.get('ir.sequence').get(cr, uid, 'salary.slip')
            ttyme = datetime.fromtimestamp(time.mktime(time.strptime(slip.date,"%Y-%m-%d")))
            update.update({
                'deg_id':function,
                'number':number, 
                'basic': round(basic),
                'basic_before_leaves': round(basic),
                'name':'Salary Slip of %s for %s' % (slip.employee_id.name, ttyme.strftime('%B-%Y')), 
                'state':'draft',
                'contract_id':contract.id,
                'company_id':slip.employee_id.company_id.id
            })
            self.write(cr, uid, [slip.id], update)
        
            if contract:
                for slip in self.browse(cr, uid, ids):
                    basic_before_leaves = basic

                    working_day = 0
                    off_days = 0
                    dates = prev_bounds(slip.date)
                    
                    days_arr = [0, 1, 2, 3, 4, 5, 6]
                    for dy in range(contract.working_days_per_week, 7):
                        off_days += get_days(1, dates[1].day, dates[1].month, dates[1].year, days_arr[dy])
                
                    total_off = off_days
                    working_day = dates[1].day - total_off
                    perday = slip.net / working_day
                    
                    total = 0.0
                    leave = 0.0
                    
                    leave_ids = self._get_leaves(cr, uid, slip, slip.employee_id, context)
                    
                    total_leave = 0.0
                    paid_leave = 0.0
                    for hday in holiday_pool.browse(cr, uid, leave_ids):
                        res = {
                            'slip_id':slip.id,
                            'name':hday.holiday_status_id.name + '-%s' % (hday.number_of_days),
                            'code':hday.holiday_status_id.code,
                            'amount_type':'fix',
                            'category_id':hday.holiday_status_id.head_id.id,
                            'account_id':hday.holiday_status_id.account_id.id,
                            'analytic_account_id':hday.holiday_status_id.analytic_account_id.id
                        }
                        
                        days = hday.number_of_days
                        if hday.number_of_days < 0:
                            days = hday.number_of_days * -1
                        
                        total_leave += days
                        if hday.holiday_status_id.type == 'paid':
                            paid_leave += days
                            continue
                            
                        elif hday.holiday_status_id.type == 'halfpaid':
                            paid_leave += (days / 2)
                            res['name'] = hday.holiday_status_id.name + '-%s/2' % (days)
                            res['amount'] = perday * (days/2)
                            total += perday * (days/2)
                            leave += days / 2
                            res['type'] = 'deduction'
                        else:
                            res['name'] = hday.holiday_status_id.name + '-%s' % (days)
                            res['amount'] = perday * days
                            res['type'] = 'deduction'
                            leave += days
                            total += perday * days
                        
                        slip_line_pool.create(cr, uid, res)
                    basic = basic - total
                    leaves = total

                    update.update({
                        'basic_before_leaves': round(basic_before_leaves),
                        'leaves':total,
                        'holiday_days':leave,
                        'worked_days':working_day - leave,
                        'working_days':working_day,
                    })
                    self.write(cr, uid, [slip.id], update)
                
        return True
        
hr_payslip()

class line_condition(osv.osv):
    '''
    Line Condition
    '''
    _name = 'hr.payslip.line.condition'
    _description = 'Line Condition'
    
    _columns = {
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'date_start': fields.date('Start Date'),
        'date_end': fields.date('End Date'),
        'state':fields.selection([
            ('total','Override By'),
            ('add','Add to Structure')
        ],'Condition', select=True, readonly=False),
    }
line_condition()

class hr_payslip_line(osv.osv):
    '''
    Payslip Line
    '''
    _name = 'hr.payslip.line'
    _description = 'Payslip Line'
    
    def onchange_category(self, cr, uid, ids, category_id):
        seq = 0
        res = {
        }
        if category_id:
            category = self.pool.get('hr.allounce.deduction.categoty').browse(cr, uid, category_id)
            res.update({
                'sequence':category.sequence,
                'name':category.name,
                'code':category.code,
                'type':category.type
            })
        return {'value':res}
    
    def onchange_amount(self, cr, uid, ids, amount, typ):
        amt = amount
        if typ and typ == 'per':
            if int(amt) > 0:
                amt = amt / 100
        return {'value':{'amount':amt}}
    
    _columns = {
        'slip_id':fields.many2one('hr.payslip', 'Pay Slip', required=False),
        'condition_id':fields.many2one('hr.payslip.line.condition', 'Condition', required=False),
        'function_id':fields.many2one('hr.payroll.structure', 'Function', required=False),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'base':fields.char('Formula', size=1024, required=False, readonly=False),
        'code':fields.char('Code', size=64, required=False, readonly=False),
        'type':fields.selection([
            ('allowance','Allowance'),
            ('deduction','Deduction'),
            ('leaves','Leaves'),
            ('advance','Advance'),
            ('loan','Loan'),
            ('installment','Loan Installment'),
            ('otherpay','Other Payment'),
            ('otherdeduct','Other Deduction'),
        ],'Type', select=True, required=True),
        'category_id':fields.many2one('hr.allounce.deduction.categoty', 'Category', required=True),
        'amount_type':fields.selection([
            ('per','Percentage (%)'),
            ('fix','Fixed Amount'),
            ('func','Function Value'),
        ],'Amount Type', select=True),
        'amount': fields.float('Amount / Percentage', digits=(16, 4)),
        'analytic_account_id':fields.many2one('account.analytic.account', 'Analytic Account', required=False),
        'account_id':fields.many2one('account.account', 'General Account', required=True),
        'total': fields.float('Sub Total', readonly=True, digits=(16, int(config['price_accuracy']))),
        #'total': fields.function(_calculate, method=True, type='float', string='Label', store=True),
        'company_contrib': fields.float('Company Contribution', readonly=True, digits=(16, int(config['price_accuracy']))),
        'expanse_id': fields.many2one('hr.expense.expense', 'Expense'),
        'sequence': fields.integer('Sequence'),
        'note':fields.text('Description'),
        'line_ids':fields.one2many('hr.payslip.line.line', 'slipline_id', 'Calculations', required=False)
    }
    _order = 'sequence'
    
    def execute_function(self, cr, uid, id, value, context):
        line_pool = self.pool.get('hr.payslip.line.line')
        res = 0
        ids = line_pool.search(cr, uid, [('slipline_id','=',id), ('from_val','<=',value), ('to_val','>=',value)])
        
        if not ids:
            ids = line_pool.search(cr, uid, [('slipline_id','=',id), ('from_val','<=',value)])
        
        if not ids:
            return res
        
        res = line_pool.browse(cr, uid, ids)[-1].value
        return res
        
hr_payslip_line()

class hr_payslip_line_line(osv.osv):
    '''
    Function Line
    '''
    _name = 'hr.payslip.line.line'
    _description = 'Function Line'
    _order = 'sequence'
    
    _columns = {
        'slipline_id':fields.many2one('hr.payslip.line', 'Slip Line', required=False),
        'name':fields.char('Name', size=64, required=False, readonly=False),
        'umo_id':fields.many2one('product.uom', 'Unite', required=False),
        'from_val': fields.float('From', digits=(16, int(config['price_accuracy']))),
        'to_val': fields.float('To', digits=(16, int(config['price_accuracy']))),
        'amount_type':fields.selection([
            ('fix','Fixed Amount'),
        ],'Amount Type', select=True),
        'sequence':fields.integer('Sequence'),
        'value': fields.float('Value', digits=(16, int(config['price_accuracy']))),
    }
hr_payslip_line_line()

class hr_employee(osv.osv):
    '''
    Employee
    '''
    _inherit = 'hr.employee'
    _description = 'Employee'
    
    _columns = {
        'pan_no':fields.char('PAN No', size=64, required=False, readonly=False),
        'esp_account':fields.char('EPS Account', size=64, required=False, readonly=False),
        'pf_account':fields.char('PF Account', size=64, required=False, readonly=False),
        'pg_joining': fields.date('PF Join Date'),
        'esi_account':fields.char('ESI Account', size=64, required=False, readonly=False),
        'hospital_id':fields.many2one('res.partner.address', 'ESI Hospital', required=False),
        'passport_id':fields.many2one('hr.passport', 'Passport', required=False),
        'bank_account_id':fields.many2one('res.partner.bank', 'Bank Account', required=False),
        'line_ids':fields.one2many('hr.payslip.line', 'employee_id', 'Salary Structure', required=False),
        'slip_ids':fields.one2many('hr.payslip', 'employee_id', 'Payslips', required=False, readonly=True),
        'property_bank_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Bank Account",
            method=True,
            view_load=True,
            help="Select Bank Account from where Salary Expanse will be Paid",
            required=True),
        'salary_account':fields.property(
            'account.account',  
            type='many2one',
            relation='account.account',
            string="Salary Account",
            method=True,
            view_load=True,
            help="Expanse account when Salary Expanse will be recorded",
            required=True),
        'employee_account':fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Employee Account",
            method=True,
            view_load=True,
            help="Employee Payable Account",
            required=True),
        'analytic_account':fields.property(
            'account.analytic.account',
            type='many2one',
            relation='account.analytic.account',
            string="Analytic Account",
            method=True,
            view_load=True,
            help="Analytic Account for Salary Analysis",
            required=False),
    }
hr_employee()

