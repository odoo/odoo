#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from datetime import date
from datetime import datetime
from datetime import timedelta

import netsvc
from osv import fields, osv
import tools
from tools.translate import _
import decimal_precision as dp

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


class hr_payroll_structure(osv.osv):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions
    """

    _name = 'hr.payroll.structure'
    _description = 'Salary Structure'
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, readonly=False),
#        'line_ids':fields.one2many('hr.payslip.line', 'function_id', 'Salary Structure', required=False),
        'company_id':fields.many2one('res.company', 'Company', required=True),
        'note': fields.text('Description'),
        'parent_id':fields.many2one('hr.payroll.structure', 'Parent'),
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
        default = {
            'code': self.browse(cr, uid, id, context=context).code+"(copy)",
            'company_id': self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        }
        return super(hr_payroll_structure, self).copy(cr, uid, id, default, context=context)

hr_payroll_structure()

class hr_contract(osv.osv):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """

    _inherit = 'hr.contract'
    _description = 'Employee Contract'
    _columns = {
        'struct_id': fields.many2one('hr.payroll.structure', 'Salary Structure'),
        'basic': fields.float('Basic Salary', digits_compute=dp.get_precision('Account')),
    }

hr_contract()

class payroll_register(osv.osv):
    """
    Payroll Register
    """

    _name = 'hr.payroll.register'
    _description = 'Payroll Register'

#    def _calculate(self, cr, uid, ids, field_names, arg, context=None):
#        res = {}
#        allounce = 0.0
#        deduction = 0.0
#        net = 0.0
#        grows = 0.0
#        for register in self.browse(cr, uid, ids, context=context):
#            for slip in register.line_ids:
#                allounce += slip.allounce
#                deduction += slip.deduction
##                net += slip.net
##                grows += slip.grows
#
#            res[register.id] = {
#                'allounce':allounce,
#                'deduction':deduction,
##                'net':net,
##                'grows':grows
#            }
#        return res

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
        'active':fields.boolean('Active', required=False),
        'company_id':fields.many2one('res.company', 'Company', required=False),
#        'grows': fields.function(_calculate, method=True, store=True, multi='dc', string='Gross Salary', type='float', digits=(16, 4)),
#        'net': fields.function(_calculate, method=True, store=True, multi='dc', string='Net Salary', digits=(16, 4)),
#        'allounce': fields.function(_calculate, method=True, store=True, multi='dc', string='Allowance', digits=(16, 4)),
#        'deduction': fields.function(_calculate, method=True, store=True, multi='dc', string='Deduction', digits=(16, 4)),
        'note': fields.text('Description'),
        'bank_id':fields.many2one('res.bank', 'Bank', required=False, help="Select the Bank Address from which the salary is going to be paid"),
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': 'new',
        'active': True,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }

    def compute_sheet(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}

        vals = self.browse(cr, uid, ids[0], context=context)
        emp_ids = emp_pool.search(cr, uid, [], context=context)

        for emp in emp_pool.browse(cr, uid, emp_ids, context=context):
            old_slips = slip_pool.search(cr, uid, [('employee_id','=', emp.id), ('date','=',vals.date)], context=context)
            if old_slips:
                slip_pool.write(cr, uid, old_slips, {'register_id':ids[0]}, context=context)
#                for sid in old_slips:
#                    wf_service.trg_validate(uid, 'hr.payslip', sid, 'compute_sheet', cr)
            else:
                res = {
                    'employee_id':emp.id,
                    'basic':0.0,
                    'register_id':ids[0],
                    'name':vals.name,
                    'date':vals.date,
                }
                slip_id = slip_pool.create(cr, uid, res, context=context)
#                wf_service.trg_validate(uid, 'hr.payslip', slip_id, 'compute_sheet', cr)

        number = self.pool.get('ir.sequence').get(cr, uid, 'salary.register')
        self.write(cr, uid, ids, {'state': 'draft', 'number': number}, context=context)
        return True

    def set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True

    def cancel_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return True

    def verify_sheet(self, cr, uid, ids, context=None):
        slip_pool = self.pool.get('hr.payslip')

        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id)], context=context)
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'verify_sheet', cr)

        self.write(cr, uid, ids, {'state':'hr_check'}, context=context)
        return True

    def final_verify_sheet(self, cr, uid, ids, context=None):
        slip_pool = self.pool.get('hr.payslip')
#        advice_pool = self.pool.get('hr.payroll.advice')
#        advice_line_pool = self.pool.get('hr.payroll.advice.line')
        sequence_pool = self.pool.get('ir.sequence')
        users_pool = self.pool.get('res.users')

        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id), ('state','=','hr_check')], context=context)
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'final_verify_sheet', cr)

        company_name = users_pool.browse(cr, uid, uid, context=context).company_id.name
        self.write(cr, uid, ids, {'state':'confirm'}, context=context)
        return True

    def process_sheet(self, cr, uid, ids, context=None):
        slip_pool = self.pool.get('hr.payslip')
        for id in ids:
            sids = slip_pool.search(cr, uid, [('register_id','=',id), ('state','=','confirm')], context=context)
            wf_service = netsvc.LocalService("workflow")
            for sid in sids:
                wf_service.trg_validate(uid, 'hr.payslip', sid, 'process_sheet', cr)

        self.write(cr, uid, ids, {'state':'done'}, context=context)
        return True

payroll_register()

class contrib_register(osv.osv):
    '''
    Contribution Register
    '''

    _name = 'hr.contibution.register'
    _description = 'Contribution Register'

    def _total_contrib(self, cr, uid, ids, field_names, arg, context=None):
        line_pool = self.pool.get('hr.contibution.register.line')

        res = {}
        for cur in self.browse(cr, uid, ids, context=context):
            current = line_pool.search(cr, uid, [('register_id','=',cur.id)], context=context)
            e_month = 0.0
            c_month = 0.0
            for i in line_pool.browse(cr, uid, current, context=context):
                e_month += i.emp_deduction
                c_month += i.comp_deduction
            res[cur.id]={
                'monthly_total_by_emp':e_month,
                'monthly_total_by_comp':c_month,
            }
        return res

    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'register_line_ids':fields.one2many('hr.contibution.register.line', 'register_id', 'Register Line', readonly=True),
        'monthly_total_by_emp': fields.function(_total_contrib, method=True, multi='dc', string='Total By Employee', digits=(16, 4)),
        'monthly_total_by_comp': fields.function(_total_contrib, method=True, multi='dc', string='Total By Company', digits=(16, 4)),
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

    def _total(self, cr, uid, ids, field_names, arg, context=None):
        res={}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.emp_deduction + line.comp_deduction
            return res

    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'register_id':fields.many2one('hr.contibution.register', 'Register', required=False),
        'code':fields.char('Code', size=64, required=False, readonly=False),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'date': fields.date('Date'),
        'emp_deduction': fields.float('Employee Deduction', digits=(16, 4)),
        'comp_deduction': fields.float('Company Deduction', digits=(16, 4)),
        'total': fields.function(_total, method=True, store=True,  string='Total', digits=(16, 4)),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }
contrib_register_line()

class hr_salary_head_type(osv.osv):
    """
    Salary Head Type
    """

    _name = 'hr.salary.head.type'
    _description = 'Salary Head Type'
    _columns = {
        'name':fields.char('Type Name', size=64, required=True, readonly=False),
        'code':fields.char('Type Code', size=64, required=True, readonly=False),
    }

hr_salary_head_type()

class hr_salary_head(osv.osv):
    """
    Salary Head
    """

    _name = 'hr.salary.head'
    _description = 'Salary Head'
    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, readonly=False),
        'type':fields.many2one('hr.salary.head.type', 'Type', required=True, help="It is used only for the reporting purpose."),
        'note': fields.text('Description'),
        'user_id':fields.char('User', size=64, required=False, readonly=False),
        'state':fields.char('Label', size=64, required=False, readonly=False),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'dispaly_payslip_report': fields.boolean('Display on Payslip Report', help="Used for the display of head on Payslip Report."),
#        'computation_based':fields.selection([
#            ('rules','List of Rules'),
#            ('exp','Expression'),
#        ],'Computation Based On', select=True, required=True),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'dispaly_payslip_report': 1,
    }
hr_salary_head()

class hr_holidays_status(osv.osv):

    _inherit = "hr.holidays.status"
    _columns = {
        'code':fields.char('Code', size=64, required=False, readonly=False, help="It is used to define the code for Leave Type which will then be used in Salary Rules."),
    }
hr_holidays_status()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''

    _name = 'hr.payslip'
    _description = 'Pay Slip'

    def _calculate(self, cr, uid, ids, field_names, arg, context=None):
        if not ids: return {}
        slip_line_obj = self.pool.get('hr.payslip.line')
        res = {}
        for rs in self.browse(cr, uid, ids, context=context):
            allow = 0.0
            deduct = 0.0
            others = 0.0
            contract = rs.employee_id.contract_id
            obj = {'basic':contract.wage}
#            if rs.igross > 0:
#                obj['gross'] = rs.igross
#            if rs.inet > 0:
#                obj['net'] = rs.inet
            for line in rs.line_ids:
                amount = 0.0
                if line.amount_type == 'per':
                    try:
                        amount = line.amount * eval(str(line.category_id.base), obj)
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
                elif line.amount_type in ('fix'):
                    amount = line.amount
                cd = line.category_id.code.lower()
                obj[cd] = amount
                contrib = 0.0
                if line.type.name == 'allowance':
                    allow += amount
                    others += contrib
                    amount -= contrib
                elif line.type.name == 'deduction':
                    deduct += amount
                    others -= contrib
                    amount += contrib
                slip_line_obj.write(cr, uid, [line.id], {'total':amount}, context=context)

            record = {
                'allounce':allow,
                'deduction':deduct,
                'grows':rs.basic + allow,
                'net':rs.basic + allow - deduct,
                'other_pay':others,
                'state': 'draft',
                'total_pay': abs(contract.wage + allow - deduct)
            }
            res[rs.id] = record
        return res

    _columns = {
        'struct_id':fields.many2one('hr.payroll.structure', 'Designation', readonly=True, states={'new': [('readonly', False)], 'draft': [('readonly', False)]}),
        'register_id':fields.many2one('hr.payroll.register', 'Register', required=False, readonly=True, states={'new': [('readonly', False)]}),
        'name':fields.char('Name', size=64, required=False, readonly=True, states={'new': [('readonly', False)]}),
        'number':fields.char('Number', size=64, required=False, readonly=True, states={'new': [('readonly', False)]}),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True, readonly=True, states={'new': [('readonly', False)], 'draft': [('readonly', False)]}),
        'date': fields.date('Date', readonly=True, states={'new': [('readonly', False)]}),
        'state':fields.selection([
            ('new','New Slip'),
            ('draft','Wating for Verification'),
            ('hr_check','Wating for HR Verification'),
            ('accont_check','Wating for Account Verification'),
            ('confirm','Confirm Sheet'),
            ('done','Paid Salary'),
            ('cancel','Reject'),
        ],'State', select=True, readonly=True),
        'basic_before_leaves': fields.float('Basic Salary', readonly=True,  digits_compute=dp.get_precision('Account')),
        'leaves': fields.float('Leave Deductions', readonly=True,  digits_compute=dp.get_precision('Account')),
        'basic': fields.float('Net Basic', readonly=True,  digits_compute=dp.get_precision('Account')),
        'grows': fields.function(_calculate, method=True, store=True, multi='dc', string='Gross Salary', digits_compute=dp.get_precision('Account')),
        'net': fields.function(_calculate, method=True, store=True, multi='dc', string='Net Salary', digits_compute=dp.get_precision('Account')),
        'allounce': fields.function(_calculate, method=True, store=True, multi='dc', string='Allowance', digits_compute=dp.get_precision('Account')),
        'deduction': fields.function(_calculate, method=True, store=True, multi='dc', string='Deduction', digits_compute=dp.get_precision('Account')),
        'other_pay': fields.function(_calculate, method=True, store=True, multi='dc', string='Others', digits_compute=dp.get_precision('Account')),
        'total_pay': fields.function(_calculate, method=True, store=True, multi='dc', string='Total Payment', digits_compute=dp.get_precision('Account')),
#        'total_pay': fields.float('Total Payment', readonly=True,  digits_compute=dp.get_precision('Account')),
        'line_ids':fields.one2many('hr.payslip.line', 'slip_id', 'Payslip Line', required=False, readonly=True, states={'new': [('readonly', False)], 'draft': [('readonly', False)]}),
        'company_id':fields.many2one('res.company', 'Company', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'holiday_days': fields.float('No of Leaves', readonly=True),
        'worked_days': fields.float('Worked Day', readonly=True),
        'working_days': fields.float('Working Days', readonly=True),
        'paid':fields.boolean('Paid ? ', required=False, readonly=True, states={'new': [('readonly', False)], 'draft': [('readonly', False)]}),
        'note':fields.text('Description'),
        'contract_id':fields.many2one('hr.contract', 'Contract', required=False, readonly=True, states={'new': [('readonly', False)],'draft': [('readonly', False)]}),
#        'igross': fields.float('Calculaton Field', readonly=True,  digits=(16, 2), help="Calculation field used for internal calculation, do not place this on form"),
#        'inet': fields.float('Calculaton Field', readonly=True,  digits=(16, 2), help="Calculation field used for internal calculation, do not place this on form"),
        'holiday_ids':fields.one2many('hr.holidays', 'payslip_id', 'Payslip', required=False),
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
        res_id = super(hr_payslip, self).copy(cr, uid, id, default, context=context)
        return res_id

    def create_voucher(self, cr, uid, ids, name, voucher, sequence=5):
        slip_move = self.pool.get('hr.payslip.account.move')
        for slip in ids:
            res = {
                'slip_id':slip,
                'move_id':voucher,
                'sequence':sequence,
                'name':name
            }
            slip_move.create(cr, uid, res)

    def set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True

    def cancel_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'cancel'}, context=context)
        return True

    def account_check_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'accont_check'}, context=context)
        return True

    def hr_check_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'hr_check'}, context=context)
        return True

    def process_sheet(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'paid':True, 'state':'done'}, context=context)
        return True

    def verify_sheet(self, cr, uid, ids, context=None):
#        register_pool = self.pool.get('company.contribution')
        register_line_pool = self.pool.get('hr.contibution.register.line')

        for slip in self.browse(cr, uid, ids, context=context):
            base = {
                'basic':slip.basic,
#                'net':slip.net,
#                'gross':slip.grows,
            }
#            rules = slip.contract_id.struct_id.rule_ids
#            if rules:
#                for rl in rules:
#                    if rl.contribute_ids:
#                        base[rl.code.lower()] = rl.amount
#                        for contrib in rl.contribute_ids:
#                            if contrib.register_id:
#                                value = eval(rl.category_id.base, base)
#                                company_contrib = register_pool.compute(cr, uid, contrib.id, value, context)
#                                reg_line = {
#                                    'name':rl.name,
#                                    'register_id': contrib.register_id.id,
#                                    'code':rl.code,
#                                    'employee_id':slip.employee_id.id,
#                                    'emp_deduction':rl.amount,
#                                    'comp_deduction':company_contrib,
#                                    'total':rl.amount + rl.amount
#                                }
#                                register_line_pool.create(cr, uid, reg_line)

        self.write(cr, uid, ids, {'state':'confirm'}, context=context)
        return True

    def get_contract(self, cr, uid, employee, date, context=None):
#        sql_req= '''
#            SELECT c.id as id, c.wage as wage, struct_id as function
#            FROM hr_contract c
#              LEFT JOIN hr_employee emp on (c.employee_id=emp.id)
#              LEFT JOIN hr_contract_wage_type cwt on (cwt.id = c.wage_type_id)
#              LEFT JOIN hr_contract_wage_type_period p on (cwt.period_id = p.id)   #PSI@ improve as we need period but wage_type_id field removed
#            WHERE
#              (emp.id=%s) AND
#              (date_start <= %s) AND
#              (date_end IS NULL OR date_end >= %s)
#            LIMIT 1
#            '''
        sql_req= '''
            SELECT c.id as id, c.wage as wage, struct_id as function
            FROM hr_contract c
              LEFT JOIN hr_employee emp on (c.employee_id=emp.id)
            WHERE
              (emp.id=%s) AND
              (date_start <= %s) AND
              (date_end IS NULL OR date_end >= %s)
            LIMIT 1
            '''
        cr.execute(sql_req, (employee.id, date, date))
        contract = cr.dictfetchone()

        contract = contract and contract or {}
        return contract

    def _get_leaves(self, cr, user, slip, employee, context=None):
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

    def _get_leaves1(self, cr, user, ddate, employee, context=None):
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

        dates = prev_bounds(ddate)
        sql = '''select id from hr_holidays
                    where date_from >= '%s' and date_to <= '%s'
                    and employee_id = %s
                    ''' % (dates[0], dates[1], employee.id)
        cr.execute(sql)
        res = cr.fetchall()
        if res:
            result = [x[0] for x in res]
        return result

#    def compute_sheet(self, cr, uid, ids, context=None):
#        func_pool = self.pool.get('hr.payroll.structure')
#        slip_line_pool = self.pool.get('hr.payslip.line')
#        holiday_pool = self.pool.get('hr.holidays')
#        sequence_obj = self.pool.get('ir.sequence')
#        if context is None:
#            context = {}
#        date = self.read(cr, uid, ids, ['date'], context=context)[0]['date']
#        #Check for the Holidays
#        def get_days(start, end, month, year, calc_day):
#            import datetime
#            count = 0
#            for day in range(start, end):
#                if datetime.date(year, month, day).weekday() == calc_day:
#                    count += 1
#            return count
#
#        for slip in self.browse(cr, uid, ids, context=context):
#            old_slip_ids = slip_line_pool.search(cr, uid, [('slip_id','=',slip.id)], context=context)
#            slip_line_pool.unlink(cr, uid, old_slip_ids, context=context)
#            update = {}
#            ttyme = datetime.fromtimestamp(time.mktime(time.strptime(slip.date,"%Y-%m-%d")))
#            contracts = self.get_contract(cr, uid, slip.employee_id, date, context)
#            if contracts.get('id', False) == False:
#                update.update({
#                    'basic': round(0.0),
#                    'basic_before_leaves': round(0.0),
#                    'name':'Salary Slip of %s for %s' % (slip.employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#                    'state':'draft',
#                    'contract_id':False,
#                    'company_id':slip.employee_id.company_id.id
#                })
#                self.write(cr, uid, [slip.id], update, context=context)
#                continue
#
#            contract = slip.employee_id.contract_id
##            sal_type = contract.wage_type_id.type
#            function = contract.struct_id.id
#            lines = []
#            if function:
#                func = func_pool.read(cr, uid, function, ['line_ids'], context=context)
#                lines = slip_line_pool.browse(cr, uid, func['line_ids'], context=context)
#
#            #lines += slip.employee_id.line_ids
#
#            ad = []
#            all_per = 0.0
#            ded_per = 0.0
#            all_fix = 0.0
#            ded_fix = 0.0
#
#            obj = {'basic':0.0}
##            if contract.wage_type_id.type == 'gross':
##                obj['gross'] = contract.wage
##                update['igross'] = contract.wage
##            if contract.wage_type_id.type == 'net':
##                obj['net'] = contract.wage
##                update['inet'] = contract.wage
##            if contract.wage_type_id.type == 'basic':
##                obj['basic'] = contract.wage
##                update['basic'] = contract.wage
#
#            for line in lines:
#                cd = line.code.lower()
#                obj[cd] = line.amount or 0.0
#
#            for line in lines:
#                if line.category_id.code in ad:
#                    continue
#                ad.append(line.category_id.code)
#                cd = line.category_id.code.lower()
#                calculate = False
#                try:
#                    exp = line.category_id.condition
#                    calculate = eval(exp, obj)
#                except Exception, e:
#                    raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#
#                if not calculate:
#                    continue
#
#                percent = 0.0
#                value = 0.0
#                base = False
##                company_contrib = 0.0
#                base = line.category_id.base
#
#                try:
#                    #Please have a look at the configuration guide.
#                    amt = eval(base, obj)
#                except Exception, e:
#                    raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#
##                if sal_type in ('gross', 'net'):
##                    if line.amount_type == 'per':
##                        percent = line.amount
##                        if amt > 1:
##                            value = percent * amt
##                        elif amt > 0 and amt <= 1:
##                            percent = percent * amt
##                        if value > 0:
##                            percent = 0.0
##                    elif line.amount_type == 'fix':
##                        value = line.amount
##                    elif line.amount_type == 'func':
##                        value = slip_line_pool.execute_function(cr, uid, line.id, amt, context)
##                        line.amount = value
##                else:
#                if line.amount_type in ('fix', 'per'):
#                    value = line.amount
#                elif line.amount_type == 'func':
#                    value = slip_line_pool.execute_function(cr, uid, line.id, amt, context)
#                    line.amount = value
#                if line.type == 'allowance':
#                    all_per += percent
#                    all_fix += value
#                elif line.type == 'deduction':
#                    ded_per += percent
#                    ded_fix += value
#                vals = {
#                    'amount':line.amount,
#                    'slip_id':slip.id,
#                    'employee_id':False,
#                    'function_id':False,
#                    'base':base
#                }
#                slip_line_pool.copy(cr, uid, line.id, vals, {})
##            if sal_type in ('gross', 'net'):
##                sal = contract.wage
##                if sal_type == 'net':
##                    sal += ded_fix
##                sal -= all_fix
##                per = 0.0
##                if sal_type == 'net':
##                    per = (all_per - ded_per)
##                else:
##                    per = all_per
##                if per <=0:
##                    per *= -1
##                final = (per * 100) + 100
##                basic = (sal * 100) / final
##            else:
#            basic = contract.wage
#
#            number = sequence_obj.get(cr, uid, 'salary.slip')
#            update.update({
#                'struct_id':function,
#                'number':number,
#                'basic': round(basic),
#                'basic_before_leaves': round(basic),
#                'name':'Salary Slip of %s for %s' % (slip.employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#                'state':'draft',
#                'contract_id':contract.id,
#                'company_id':slip.employee_id.company_id.id
#            })
#
#            for line in slip.employee_id.line_ids:
#                vals = {
#                    'amount':line.amount,
#                    'slip_id':slip.id,
#                    'employee_id':False,
#                    'function_id':False,
#                    'base':base
#                }
#                slip_line_pool.copy(cr, uid, line.id, vals, {})
#
#            self.write(cr, uid, [slip.id], update, context=context)
#
#        for slip in self.browse(cr, uid, ids, context=context):
#            if not slip.contract_id:
#                continue
#
#            basic_before_leaves = slip.basic
#            working_day = 0
#            off_days = 0
#            dates = prev_bounds(slip.date)
#
#            days_arr = [0, 1, 2, 3, 4, 5, 6]
#            for dy in range(slip.employee_id.contract_id.working_days_per_week, 7):
#                off_days += get_days(1, dates[1].day, dates[1].month, dates[1].year, days_arr[dy])
#            total_off = off_days
#            working_day = dates[1].day - total_off
#            perday = slip.basic / working_day
#            total = 0.0
#            leave = 0.0
#            leave_ids = self._get_leaves(cr, uid, slip, slip.employee_id, context)
#            total_leave = 0.0
#            paid_leave = 0.0
#            h_ids = holiday_pool.browse(cr, uid, leave_ids, context=context)
#            for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
#                if not hday.holiday_status_id.head_id:
#                    raise osv.except_osv(_('Error !'), _('Please check configuration of %s, payroll head is missing') % (hday.holiday_status_id.name))
#
#                res = {
#                    'slip_id':slip.id,
#                    'name':hday.holiday_status_id.name + '-%s' % (hday.number_of_days),
#                    'code':hday.holiday_status_id.code,
#                    'amount_type':'fix',
#                    'category_id':hday.holiday_status_id.head_id.id,
#                    'sequence':hday.holiday_status_id.head_id.sequence
#                }
#                days = hday.number_of_days
#                if hday.number_of_days < 0:
#                    days = hday.number_of_days * -1
#                total_leave += days
#                if hday.holiday_status_id.type == 'paid':
#                    paid_leave += days
#                    continue
##                    res['name'] = hday.holiday_status_id.name + '-%s' % (days)
##                    res['amount'] = perday * days
##                    res['type'] = 'allowance'
##                    leave += days
##                    total += perday * days
#
#                elif hday.holiday_status_id.type == 'halfpaid':
#                    paid_leave += (days / 2)
#                    res['name'] = hday.holiday_status_id.name + '-%s/2' % (days)
#                    res['amount'] = perday * (days/2)
#                    total += perday * (days/2)
#                    leave += days / 2
#                    res['type'] = 'deduction'
#                else:
#                    res['name'] = hday.holiday_status_id.name + '-%s' % (days)
#                    res['amount'] = perday * days
#                    res['type'] = 'deduction'
#                    leave += days
#                    total += perday * days
#
#                slip_line_pool.create(cr, uid, res, context=context)
#            holiday_pool.write(cr, uid, leave_ids, {'payslip_id': slip.id}, context=context)
#            basic = basic - total
##            leaves = total
#            update.update({
#                'basic':basic,
#                'basic_before_leaves': round(basic_before_leaves),
#                'leaves':total,
#                'holiday_days':leave,
#                'worked_days':working_day - leave,
#                'working_days':working_day,
#            })
#            self.write(cr, uid, [slip.id], update, context=context)
#        return True

    def onchange_employee_id(self, cr, uid, ids, ddate, employee_id, context=None):
        func_pool = self.pool.get('hr.payroll.structure')
        slip_line_pool = self.pool.get('hr.payslip.line')
        holiday_pool = self.pool.get('hr.holidays')
        sequence_obj = self.pool.get('ir.sequence')
        empolyee_obj = self.pool.get('hr.employee')
        hr_all_ded_cate = self.pool.get('hr.allounce.deduction.categoty')
        resource_attendance_pool = self.pool.get('resource.calendar.attendance')
        if context is None:
            context = {}

        old_slip_ids = ids and slip_line_pool.search(cr, uid, [('slip_id', '=', ids[0])], context=context) or False
        if old_slip_ids:
            slip_line_pool.unlink(cr, uid, old_slip_ids)

        update = {'value':{'line_ids':[], 'holiday_ids':[], 'name':'', 'working_days': 0.0, 'holiday_days': 0.0, 'worked_days': 0.0, 'basic_before_leaves': 0.0, 'basic': 0.0, 'leaves': 0.0, 'total_pay': 0.0}}
        if not employee_id:
            return update

        if not employee_id and ids:
            old_slip_ids = slip_line_pool.search(cr, uid, [('slip_id', '=', ids[0])], context=context)
            if old_slip_ids:
                line_pool.unlink(cr, uid, old_slip_ids)
            return update

        #Check for the Holidays
        def get_days(start, end, month, year, calc_day):
            import datetime
            count = 0
            for day in range(start, end+1):
                if datetime.date(year, month, day).weekday() == calc_day:
                    count += 1
            return count

        employee_id = empolyee_obj.browse(cr, uid, employee_id, context=context)
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(ddate,"%Y-%m-%d")))
        contracts = self.get_contract(cr, uid, employee_id, ddate, context)
        if contracts.get('id', False) == False:
            update['value'].update({
                'basic': round(0.0),
                'basic_before_leaves': round(0.0),
                'name':'Salary Slip of %s for %s' % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#                'state':'draft',
                'contract_id':False,
                'company_id':employee_id.company_id.id
            })
            return update

        contract = employee_id.contract_id
#        sal_type = contract.wage_type_id.type
        function = contract.struct_id.id
        lines = []
        if function:
            func = func_pool.read(cr, uid, function, ['line_ids'], context=context)
            lines = slip_line_pool.browse(cr, uid, func['line_ids'], context=context)
        #lines += slip.employee_id.line_ids

        ad = []
#        all_per = 0.0
#        ded_per = 0.0
#        all_fix = 0.0
#        ded_fix = 0.0
        allounce = 0.0
        deduction = 0.0

        obj = {'basic':contract.wage}
#        if contract.wage_type_id.type == 'gross':
#            obj['gross'] = contract.wage
#            update['value']['igross'] = contract.wage
#        if contract.wage_type_id.type == 'net':
#            obj['net'] = contract.wage
#            update['value']['inet'] = contract.wage
#        if contract.wage_type_id.type == 'basic':
#            obj['basic'] = contract.wage
#            update['value']['basic'] = contract.wage

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
                raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

            if not calculate:
                continue

            percent = 0.0
            value = 0.0
            base = False
#                company_contrib = 0.0
            base = line.category_id.base

            try:
                #Please have a look at the configuration guide.
                amt = eval(base, obj)
            except Exception, e:
                raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

#            if sal_type in ('gross', 'net'):
#                if line.amount_type == 'per':
#                    percent = line.amount
#                    if amt > 1:
#                        value = percent * amt
#                    elif amt > 0 and amt <= 1:
#                        percent = percent * amt
#                    if value > 0:
#                        percent = 0.0
#                elif line.amount_type == 'fix':
#                    value = line.amount
#                elif line.amount_type == 'func':
#                    value = slip_line_pool.execute_function(cr, uid, line.id, amt, context)
#                    line.amount = value
#            else:
            if line.amount_type == 'per':
                try:
                    value = line.amount * amt
                except Exception, e:
                    raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
            elif line.amount_type == 'fix':
                value = line.amount
            elif line.amount_type == 'func':
                value = slip_line_pool.execute_function(cr, uid, line.id, amt, context)
                line.amount = value
            if line.type == 'allowance':
#                all_per += percent
#                all_fix += value
                allounce += value
            elif line.type == 'deduction':
#                ded_per += percent
#                ded_fix += value
                deduction += value
            vals = {
                'category_id': line.category_id.id,
                'name': line.name,
                'sequence': line.sequence,
                'type': line.type,
                'code': line.code,
                'amount_type': line.amount_type,
                'amount':line.amount,
                'total': value,
                'slip_id':line.id,
                'employee_id':False,
                'function_id':False,
                'base':line.category_id.base
            }
            update['value']['line_ids'].append(vals)
#        if sal_type in ('gross', 'net'):
#            sal = contract.wage
#            if sal_type == 'net':
#                sal += ded_fix
#            sal -= all_fix
#            per = 0.0
#            if sal_type == 'net':
#                per = (all_per - ded_per)
#            else:
#                per = all_per
#            if per <=0:
#                per *= -1
#            final = (per * 100) + 100
#            basic = (sal * 100) / final
#        else:
        basic = contract.wage

        number = sequence_obj.get(cr, uid, 'salary.slip')
        update['value'].update({
            'struct_id':function,
            'number':number,
            'basic': round(basic),
            'basic_before_leaves': round(basic),
            'allounce': round(allounce),
            'deduction': round(deduction),
#            'total_pay': round(basic)+ allounce - deduction,
            'name':'Salary Slip of %s for %s' % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#            'state':'draft',
            'contract_id':contract.id,
            'company_id':employee_id.company_id.id
        })

        for line in employee_id.line_ids:
            vals = {
                'category_id': line.category_id.id,
                'name': line.name,
                'sequence': line.sequence,
                'type': line.type,
                'code': line.code,
                'amount_type': line.amount_type,
                'amount':line.amount,
                'slip_id':line.id,
                'employee_id':False,
                'function_id':False,
                'base':base
            }
            update['value']['line_ids'].append(vals)

        basic_before_leaves = update['value']['basic']
        working_day = 0
        off_days = 0
        dates = prev_bounds(ddate)
        calendar_id = employee_id.contract_id.working_hours.id
        if not calendar_id:
            raise osv.except_osv(_('Error !'), _("Please define working schedule on %s's contract") % (employee_id.name))
        week_days = {"0": "mon", "1": "tue", "2": "wed","3": "thu", "4": "fri", "5": "sat", "6": "sun"}
        wk_days = {}
        week_ids = resource_attendance_pool.search(cr, uid, [('calendar_id', '=', calendar_id)], context=context)
        weeks = resource_attendance_pool.read(cr, uid, week_ids, ['dayofweek'], context=context)
        for week in weeks:
            if week_days.has_key(week['dayofweek']):
                wk_days[week['dayofweek']] = week_days[week['dayofweek']]
        days_arr = [0, 1, 2, 3, 4, 5, 6]
        for dy in range(len(wk_days), 7):
            off_days += get_days(1, dates[1].day, dates[1].month, dates[1].year, days_arr[dy])
        total_off = off_days
        working_day = dates[1].day - total_off
        perday = working_day and basic / working_day or 0.0
        total = 0.0
        leave = 0.0
        leave_ids = self._get_leaves1(cr, uid, ddate, employee_id, context)
        total_leave = 0.0
        paid_leave = 0.0
        h_ids = holiday_pool.browse(cr, uid, leave_ids, context=context)
        for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
            if not hday.holiday_status_id.code:
                raise osv.except_osv(_('Error !'), _('Please check configuration of %s, payroll head is missing') % (hday.holiday_status_id.name))
            slip_lines = hr_all_ded_cate.search(cr, uid, [('code','=',hday.holiday_status_id.code)], context=context)
            head_sequence = 0
            if slip_lines:
                head_sequence = hr_all_ded_cate.read(cr, uid, slip_lines, ['sequence'], context=context)[0]['sequence']
            res = {
                'slip_id': hday.id,
                'name': hday.holiday_status_id.name + '-%s' % (hday.number_of_days),
                'code': hday.holiday_status_id.code,
                'amount_type': 'fix',
                'category_id': slip_lines and slip_lines[0],
                'sequence': head_sequence
#                'category_id': hday.holiday_status_id.head_id.id,
#                'sequence': hday.holiday_status_id.head_id.sequence
            }
            days = hday.number_of_days
            if hday.number_of_days < 0:
                days = hday.number_of_days * -1
            total_leave += days
#            if hday.holiday_status_id.type == 'paid':
#                paid_leave += days
#                continue
##                    res['name'] = hday.holiday_status_id.name + '-%s' % (days)
##                    res['amount'] = perday * days
##                    res['type'] = 'allowance'
##                    leave += days
##                    total += perday * days
#
#            elif hday.holiday_status_id.type == 'halfpaid':
#                paid_leave += (days / 2)
#                res['name'] = hday.holiday_status_id.name + '-%s/2' % (days)
#                res['amount'] = perday * (days/2)
#                total += perday * (days/2)
#                res['total'] = total
#                leave += days / 2
#                res['type'] = 'deduction'
#            else:
            res['name'] = hday.holiday_status_id.name + '-%s' % (days)
            res['amount'] = perday * days
            res['type'] = 'deduction'
            leave += days
            total += perday * days
            res['total'] = total
#            slip_line_pool.create(cr, uid, res, context=context)
            update['value']['line_ids'].append(res)
#        holiday_pool.write(cr, uid, leave_ids, {'payslip_id': ids and ids[0] or False}, context=context)
        basic = basic - total
#            leaves = total
        temp_dic = self.pool.get('hr.holidays').read(cr, uid, leave_ids, [], context=context)
        update['value'].update({
            'basic':basic,
            'basic_before_leaves': round(basic_before_leaves),
            'total_pay': round(basic_before_leaves)+ allounce - (deduction + total),
            'leaves': total,
            'holiday_days': leave,
            'worked_days': working_day - leave,
            'working_days': working_day,
#            'holiday_ids': temp_dic
        })
#        self.write(cr, uid, uid, update, context=context)
        return update

hr_payslip()



class hr_holidays(osv.osv):

    _inherit = "hr.holidays"
    _columns = {
        'payslip_id':fields.many2one('hr.payslip', 'Payslip', required=False),
    }

hr_holidays()

class hr_payslip_line(osv.osv):
    '''
    Payslip Line
    '''

    _name = 'hr.payslip.line'
    _description = 'Payslip Line'

    def onchange_category(self, cr, uid, ids, category_id):
        res = {}
        if category_id:
            category = self.pool.get('hr.salary.head').browse(cr, uid, category_id)
            res.update({
#                'sequence':category.sequence,
                'name':category.name,
                'code':category.code,
                'type':category.type.id
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
#        'function_id':fields.many2one('hr.payroll.structure', 'Function', required=False),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'base':fields.char('Formula', size=1024, required=False, readonly=False),
        'code':fields.char('Code', size=64, required=False, readonly=False),
        'category_id':fields.many2one('hr.salary.head', 'Category', required=True),
        'type':fields.many2one('hr.salary.head.type', 'Type', required=True, help="Used for the reporting purpose."),
        'amount_type':fields.selection([
            ('per','Percentage (%)'),
            ('fix','Fixed Amount'),
            ('code','Python Code'),
        ],'Amount Type', select=True, required=True),
        'amount': fields.float('Amount / Percentage', digits=(16, 4)),
        'total': fields.float('Sub Total', readonly=True, digits_compute=dp.get_precision('Account')),
        'company_contrib': fields.float('Company Contribution', readonly=True, digits=(16, 4)),
        'sequence': fields.integer('Sequence'),
        'note':fields.text('Description'),
    }
    _order = 'sequence'
    _defaults = {
        'amount_type': lambda *a: 'per'
    }

hr_payslip_line()

class hr_salary_rule(osv.osv):

    _inherit = 'hr.payslip.line'
    _name = 'hr.salary.rule'
    _columns = {
        'appears_on_payslip': fields.boolean('Appears on Payslip', help="Used for the display of rule on payslip"),
        'condition_range_min': fields.float('Minimum Range', required=False, help="The minimum amount, applied for this rule."),
        'condition_range_max': fields.float('Maximum Range', required=False, help="The maximum amount, applied for this rule."),
        'sal_rule_id':fields.many2one('hr.salary.rule', 'Parent Salary Structure', select=True),
        'child_depend':fields.boolean('Children Rule'),
        'child_ids':fields.one2many('hr.salary.rule', 'sal_rule_id', 'Child Salary Sructure'),
        'company_id':fields.many2one('res.company', 'Company', required=False),
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
        'gratuity':fields.boolean('Use for Gratuity ?', required=False),
        'computational_expression':fields.text('Computational Expression', required=True, readonly=False, help='This will use to computer the % fields values, in general its on basic, but You can use all heads code field in small letter as a variable name i.e. hra, ma, lta, etc...., also you can use, static varible basic'),
        'conditions':fields.char('Condition', size=1024, required=True, readonly=False, help='Applied this head for calculation if condition is true'),
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence'),
        'active':fields.boolean('Active', required=False),
     }
    _defaults = {
        'conditions': 'True',
        'computational_expression': 'basic',
        'sequence': 5,
        'appears_on_payslip': True,
        'active': True,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
     }

hr_salary_rule()

class hr_payroll_structure(osv.osv):

    _inherit = 'hr.payroll.structure'
    _columns = {
        'rule_ids':fields.many2many('hr.salary.rule', 'hr_structure_salary_rule_rel', 'struct_id', 'rule_id', 'Salary Rules', readonly=False),
    }

hr_payroll_structure()

class hr_employee(osv.osv):
    '''
    Employee
    '''

    _inherit = 'hr.employee'
    _description = 'Employee'

    _columns = {
        'line_ids':fields.one2many('hr.payslip.line', 'employee_id', 'Salary Structure', required=False),
        'slip_ids':fields.one2many('hr.payslip', 'employee_id', 'Payslips', required=False, readonly=True),
        'otherid': fields.char('Other Id', size=64),
#        'basic': fields.function(_calculate_salary, method=True, multi='dc', type='float', string='Basic Salary', digits=(14,2)),
#FIXME the function has to make the sum of basic field of all the hr.contract for this employee that have date_start < now() and now() < date_stop or not date_stop
#        'emp_sal_rule_ids':fields.many2many('hr.salary.rule', 'hr_emp_salary_rule_rel', 'employee_id', 'rule_id', 'Salary Rules', readonly=False),
    }
hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
