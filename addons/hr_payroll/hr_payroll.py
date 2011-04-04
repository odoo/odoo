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

def get_days(start, end, month, year, calc_day):
    import datetime
    count = 0
    for day in range(start, end):
        if datetime.date(year, month, day).weekday() == calc_day:
            count += 1
    return count

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
        'name':fields.char('Name', size=256, required=True),
        'code':fields.char('Code', size=64, required=True),
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
            'code': self.browse(cr, uid, id, context=context).code + "(copy)",
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
        'basic': fields.float('Basic Salary', digits_compute=dp.get_precision('Account')), # i think we can remove this because we have wage field on contract ?
        'schedule_pay': fields.selection([
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('semi-annually', 'Semi-annually'),
            ('annually', 'Annually'),
            ('weekly', 'Weekly'),
            ('bi-weekly', 'Bi-weekly'),
            ('bi-monthly', 'Bi-monthly'),
            ], 'Scheduled Pay', select=True),
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
            ('draft','Waiting for Verification'),
            ('hr_check','Waiting for HR Verification'),
            ('accont_check','Waiting for Account Verification'),
            ('confirm','Confirm Sheet'),
            ('done','Paid Salary'),
            ('cancel','Reject'),
        ],'State', select=True, readonly=True),
        'active':fields.boolean('Active', required=False, help="If the active field is set to false, it will allow you to hide the payroll register without removing it."),
        'company_id':fields.many2one('res.company', 'Company'),
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
                slip_pool.write(cr, uid, old_slips, {'register_id': ids[0]}, context=context)
                for sid in old_slips:
                    wf_service.trg_validate(uid, 'hr.payslip', sid, 'compute_sheet', cr)
            else:
                res = {
                    'employee_id': emp.id,
#                    'basic_amount': 0.0,
                    'register_id': ids[0],
                    'name': vals.name,
                    'date': vals.date,
                }
                slip_id = slip_pool.create(cr, uid, res, context=context)
                wf_service.trg_validate(uid, 'hr.payslip', slip_id, 'compute_sheet', cr)

        number = self.pool.get('ir.sequence').get(cr, uid, 'salary.register')
        return self.write(cr, uid, ids, {'state': 'draft', 'number': number}, context=context)

#    def compute_sheet(self, cr, uid, ids, context=None):
#        emp_pool = self.pool.get('hr.employee')
#        slip_pool = self.pool.get('hr.payslip')
#        slip_line_pool = self.pool.get('hr.payslip.line')
#        wf_service = netsvc.LocalService("workflow")
#
#        if context is None:
#            context = {}
#        vals = self.browse(cr, uid, ids[0], context=context)
#        emp_ids = emp_pool.search(cr, uid, [], context=context)
#
#        for emp in emp_pool.browse(cr, uid, emp_ids, context=context):
#            old_slips = slip_pool.search(cr, uid, [('employee_id','=', emp.id), ('date','=',vals.date)], context=context)
#            if old_slips:
#                slip_pool.write(cr, uid, old_slips, {'register_id':ids[0]}, context=context)
#            else:
#                res = {
#                    'employee_id':emp.id,
#                    'basic_amount':0.0,
#                    'register_id':ids[0],
#                    'name':vals.name,
#                    'date':vals.date,
#                }
#                slip_id = slip_pool.create(cr, uid, res, context=context)
#                data = slip_pool.onchange_employee_id(cr, uid, [slip_id], vals.date, emp.id, context=context)
#                for line in data['value']['line_ids']:
#                    line.update({'slip_id': slip_id})
#                    slip_line_pool.create(cr, uid, line, context=context)
#                data['value'].pop('line_ids')
#                slip_pool.write(cr, uid, [slip_id], data['value'], context=context)
#        number = self.pool.get('ir.sequence').get(cr, uid, 'salary.register')
#        return self.write(cr, uid, ids, {'state': 'draft', 'number': number}, context=context)

    def set_to_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def cancel_sheet(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancel'}, context=context)

    def verify_sheet(self, cr, uid, ids, context=None):
        slip_pool = self.pool.get('hr.payslip')
        wf_service = netsvc.LocalService("workflow")
        sids = slip_pool.search(cr, uid, [('register_id','in', ids)], context=context)
        for sid in sids:
            wf_service.trg_validate(uid, 'hr.payslip', sid, 'verify_sheet', cr)
        return self.write(cr, uid, ids, {'state':'hr_check'}, context=context)

    def final_verify_sheet(self, cr, uid, ids, context=None):
        slip_pool = self.pool.get('hr.payslip')
        sequence_pool = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        users_pool = self.pool.get('res.users')
        sids = slip_pool.search(cr, uid, [('register_id','in', ids), ('state','=','hr_check')], context=context)
        for sid in sids:
            wf_service.trg_validate(uid, 'hr.payslip', sid, 'final_verify_sheet', cr)
#        company_name = users_pool.browse(cr, uid, uid, context=context).company_id.name
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def process_sheet(self, cr, uid, ids, context=None):
        slip_pool = self.pool.get('hr.payslip')
        wf_service = netsvc.LocalService("workflow")
        sids = slip_pool.search(cr, uid, [('register_id','in', ids), ('state','=','confirm')], context=context)
        for sid in sids:
            wf_service.trg_validate(uid, 'hr.payslip', sid, 'process_sheet', cr)
        return self.write(cr, uid, ids, {'state':'done'}, context=context)

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
        res = {}
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
        'name':fields.char('Type Name', size=64, required=True),
        'code':fields.char('Type Code', size=16, required=True),
    }

hr_salary_head_type()

class hr_salary_head(osv.osv):
    """
    HR Salary Head
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
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence'),
#        'display_payslip_report': fields.boolean('Display on payslip report', help="Used for the display of head on Payslip Report"),
#        'computation_based':fields.selection([
#            ('rules','List of Rules'),
#            ('exp','Expression'),
#        ],'Computation Based On', select=True, required=True),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
#        'display_payslip_report': 1,
    }

hr_salary_head()

class hr_holidays_status(osv.osv):

    _inherit = "hr.holidays.status"
    _columns = {
        # improve help
        'code':fields.char('Code', size=16, readonly=False, help="It is used to define the code for Leave Type which will then be used in Salary Rules."),
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
        res = {}
        for rs in self.browse(cr, uid, ids, context=context):
            allow = 0.0
            deduct = 0.0
            others = 0.0
            for line in rs.line_ids:
                contrib = 0.0
                if line.total < 0:
                    deduct += line.total
                    others += contrib
#                    amount -= contrib
                else:
                    allow += line.total
                    others -= contrib
#                    amount += contrib
            record = {
                'allounce': allow,
                'deduction': deduct,
                'grows_amount': rs.basic_amount + allow,
                'net_amount': rs.basic_amount + allow + deduct,
                'other_pay': others,
                'state': 'draft',
                'total_pay': rs.basic_amount + allow + deduct
            }
            res[rs.id] = record
        return res

    def _get_holidays(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id] = []
            dates = prev_bounds(record.date)
            sql = '''SELECT id FROM hr_holidays
                        WHERE date_from >= '%s' AND date_to <= '%s'
                        AND employee_id = %s
                        ''' % (dates[0], dates[1], record.employee_id.id)
            if record.contract_id:
                sql += "AND contract_id = %s" % (record.contract_id.id)
            cr.execute(sql)
            res = cr.fetchall()
            if res:
                result[record.id] = [x[0] for x in res]
        return result

    def _get_parent_structure(self, cr, uid, struct_id, context=None):
        if not struct_id:
            return []
        parent = []
        for line in self.pool.get('hr.payroll.structure').browse(cr, uid, struct_id):
            if line.parent_id:
                parent.append(line.parent_id.id)
        if parent:
            parent = self._get_parent_structure(cr, uid, parent, context)
        return struct_id + parent

    def _get_salary_rules(self, cr, uid, ids, field_names, arg=None, context=None):
        structure_obj = self.pool.get('hr.payroll.structure')
        contract_obj = self.pool.get('hr.contract')
        holiday_pool = self.pool.get('hr.holidays')
        salary_rule_pool = self.pool.get('hr.salary.rule')
        res = {}
        lines = []
        rules = []
        rul = []
        structure = []
        sal_structure =[]
        contracts = []
        for record in self.browse(cr, uid, ids, context=context):
            if record.contract_id:
                contracts.append(record.contract_id)
            else:
                contracts = self.get_contract(cr, uid, record.employee_id, record.date, context=context)
            for ct in contracts:
                structure.append(ct.struct_id.id)
                leave_ids = self._get_leaves(cr, uid, record.date, record.employee_id, ct, context)
                for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
                    salary_rules = salary_rule_pool.search(cr, uid, [('code', '=', hday.holiday_status_id.code)], context=context)
                    rules +=  salary_rule_pool.browse(cr, uid, salary_rules, context=context)
            res[record.id] = {}
            for st in structure:
                sal_structure = self._get_parent_structure(cr, uid, [st], context=context)
                for struct in sal_structure:
                    lines = structure_obj.browse(cr, uid, struct, context=context).rule_ids
                    # fix me: Search rules using salary head => sequence to display rules on payslip with correct seq with salary head..
                    for rl in lines:
                        if rl.child_ids:
                            for r in rl.child_ids:
                                lines.append(r)
                        rules.append(rl)
                for fn in field_names:
#                   if fn == 'applied_salary_rule':
#                       for r in rules:
#                           if r.id not in rul:
#                               rul.append(r.id)
#                       res[record.id] = {fn: rul}
                   if fn == 'appears_on_payslip_rule':
                       for r in rules:
                           if r.appears_on_payslip:
                               if r.id not in rul:
                                   rul.append(r.id)
                       res[record.id] = {fn: rul}
                   elif fn == 'details_by_salary_head':
                       for r in rules:
                           if r.id not in rul:
                               rul.append(r.id)
                       res[record.id] = {fn: rul}
        return res

    def _compute(self, cr, uid, id, value, employee, contract, context=None):
        rule_obj = self.pool.get('hr.salary.rule')
        contrib = rule_obj.browse(cr, uid, id, context=context)
        if contrib.amount_type == 'fix':
            return contrib.amount
        elif contrib.amount_type == 'per':
            return value * contrib.amount
        elif contrib.amount_type == 'code':
            localdict = {'basic':value, 'employee':employee, 'contract':contract}
            exec contrib.python_compute in localdict
            value = localdict['result']
            return value
        return 0.0

    _columns = {
        'struct_id': fields.related('contract_id', 'struct_id', readonly=True, type='many2one', relation='hr.payroll.structure', string='Structure', store=True),
        'register_id': fields.many2one('hr.payroll.register', 'Register', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'name': fields.char('Description', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'number': fields.char('Number', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.date('Date', readonly=True, states={'draft': [('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Waiting for Verification'),
            ('hr_check', 'Waiting for HR Verification'),
            ('accont_check', 'Waiting for Account Verification'),
            ('confirm', 'Confirm Sheet'),
            ('done', 'Paid Salary'),
            ('cancel', 'Reject'),
        ], 'State', select=True, readonly=True,
            help=' * When the payslip is created the state is \'Waiting for verification\'.\
            \n* It is varified by the user and payslip is sent for HR varification, the state is \'Waiting for HR Verification\'. \
            \n* If HR varify the payslip, it is sent for account verification, the state is \'Waiting for Account Verification\'. \
            \n* It is confirmed by the accountant and the state set to \'Confirm Sheet\'.\
            \n* If the salary is paid then state is set to \'Paid Salary\'.\
            \n* The \'Reject\' state is used when user cancel payslip.'),
        'basic_before_leaves': fields.float('Basic Salary', readonly=True,  digits_compute=dp.get_precision('Account')),
        'leaves': fields.float('Leave Deductions', readonly=True,  digits_compute=dp.get_precision('Account')),
        'basic_amount': fields.related('contract_id', 'wage', type='float', relation='hr.contract', store=True, string='Basic Amount'),
        'gross_amount': fields.function(_calculate, method=True, store=True, multi='dc', string='Gross Salary', digits_compute=dp.get_precision('Account')),
        'net_amount': fields.function(_calculate, method=True, store=True, multi='dc', string='Net Salary', digits_compute=dp.get_precision('Account')),
#        'allounce': fields.function(_calculate, method=True, store=True, multi='dc', string='Allowance', digits_compute=dp.get_precision('Account')),
#        'deduction': fields.function(_calculate, method=True, store=True, multi='dc', string='Deduction', digits_compute=dp.get_precision('Account')),
#        'other_pay': fields.function(_calculate, method=True, store=True, multi='dc', string='Others', digits_compute=dp.get_precision('Account')),
        'total_pay': fields.function(_calculate, method=True, store=True, multi='dc', string='Total Payment', digits_compute=dp.get_precision('Account')),
#        'total_pay': fields.float('Total Payment', readonly=True,  digits_compute=dp.get_precision('Account')),
        'line_ids': fields.one2many('hr.payslip.line', 'slip_id', 'Payslip Line', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'holiday_days': fields.float('No of Leaves', readonly=True),
        'worked_days': fields.float('Worked Day', readonly=True),
        'working_days': fields.float('Working Days', readonly=True),
        'paid': fields.boolean('Made Payment Order ? ', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'note': fields.text('Description'),
        'contract_id': fields.many2one('hr.contract', 'Contract', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'igross': fields.float('Calculaton Field', readonly=True,  digits=(16, 2), help="Calculation field used for internal calculation, do not place this on form"),
        'inet': fields.float('Calculaton Field', readonly=True,  digits=(16, 2), help="Calculation field used for internal calculation, do not place this on form"),
        'holiday_ids': fields.function(_get_holidays, method=True, type='one2many', relation='hr.holidays', string='Holiday Lines', required=False),
#        'applied_salary_rule': fields.function(_get_salary_rules, method=True, type='one2many', relation='hr.salary.rule', string='Applied Salary Rules', multi='applied_salary_rule'),
        'appears_on_payslip_rule': fields.function(_get_salary_rules, method=True, type='one2many', relation='hr.salary.rule', string='Appears on Payslip', multi='appears_on_payslip_rule'),
        'details_by_salary_head': fields.function(_get_salary_rules, method=True, type='one2many', relation='hr.salary.rule', string='Details by Salary Head', multi='details_by_salary_head'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'state': 'draft',
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }

    def copy(self, cr, uid, id, default=None, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        default = {
            'line_ids': [],
            'move_ids': [],
            'move_line_ids': [],
            'move_payment_ids': [],
            'company_id': company_id,
            'period_id': False,
            'basic_before_leaves': 0.0,
            'basic_amount': 0.0
        }
        return super(hr_payslip, self).copy(cr, uid, id, default, context=context)
#
#    def create_voucher(self, cr, uid, ids, name, voucher, sequence=5):
#        slip_move = self.pool.get('hr.payslip.account.move')
#        for slip in ids:
#            res = {
#                'slip_id':slip,
#                'move_id':voucher,
#                'sequence':sequence,
#                'name':name
#            }
#            slip_move.create(cr, uid, res)

    def set_to_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def cancel_sheet(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

    def account_check_sheet(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'accont_check'}, context=context)

    def hr_check_sheet(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'hr_check'}, context=context)

    def process_sheet(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'paid': True, 'state': 'done'}, context=context)

    def verify_sheet(self, cr, uid, ids, context=None):
        holiday_pool = self.pool.get('hr.holidays')
        salary_rule_pool = self.pool.get('hr.salary.rule')
        structure_pool = self.pool.get('hr.payroll.structure')
        register_line_pool = self.pool.get('hr.contibution.register.line')
        contracts = []
        structures = []
        rules = []
        lines = []
        sal_structures =[]
        for slip in self.browse(cr, uid, ids, context=context):
            if slip.contract_id:
                contracts.append(slip.contract_id)
            else:
                contracts = self.get_contract(cr, uid, slip.employee_id, slip.date, context=context)
            for contract in contracts:
                structures.append(contract.struct_id.id)
                leave_ids = self._get_leaves(cr, uid, slip.date, slip.employee_id, contract, context)
                for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
                    salary_rules = salary_rule_pool.search(cr, uid, [('code', '=', hday.holiday_status_id.code)], context=context)
                    rules +=  salary_rule_pool.browse(cr, uid, salary_rules, context=context)
            for structure in structures:
                sal_structures = self._get_parent_structure(cr, uid, [structure], context=context)
                for struct in sal_structures:
                    lines = structure_pool.browse(cr, uid, struct, context=context).rule_ids
                    for line in lines:
                        if line.child_ids:
                            for r in line.child_ids:
                                lines.append(r)
                        rules.append(line)
            base = {
                'basic': slip.basic_amount,
            }
            if rules:
                for rule in rules:
                    if rule.company_contribution:
                        base[rule.code.lower()] = rule.amount
                        if rule.register_id:
                            for slip in slip.line_ids:
                                if slip.category_id == rule.category_id:
                                    line_tot = slip.total
                            value = eval(rule.computational_expression, base)
                            company_contrib = self._compute(cr, uid, rule.id, value, employee, contract, context)
                            reg_line = {
                                'name': rule.name,
                                'register_id': rule.register_id.id,
                                'code': rule.code,
                                'employee_id': slip.employee_id.id,
                                'emp_deduction': line_tot,
                                'comp_deduction': company_contrib,
                                'total': rule.amount + line_tot
                            }
                            register_line_pool.create(cr, uid, reg_line, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    def get_contract(self, cr, uid, employee, date, context=None):
        contract_obj = self.pool.get('hr.contract')
        contracts = contract_obj.search(cr, uid, [('employee_id', '=', employee.id),('date_start','<=', date),'|',('date_end', '=', False),('date_end','>=', date)], context=context)
        contract_ids = contract_obj.browse(cr, uid, contracts, context=context)
        return contract_ids or []

    def _get_leaves(self, cr, user, ddate, employee, contract, context=None):
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
        sql = '''SELECT id FROM hr_holidays
                    WHERE date_from >= '%s' AND date_to <= '%s'
                    AND employee_id = %s
                    AND state = 'validate'
                    AND contract_id = %s''' % (dates[0], dates[1], employee.id, contract.id)
        cr.execute(sql)
        res = cr.fetchall()
        if res:
            result = [x[0] for x in res]
        return result

    def compute_sheet(self, cr, uid, ids, context=None):
        func_pool = self.pool.get('hr.payroll.structure')
        slip_line_pool = self.pool.get('hr.payslip.line')
        holiday_pool = self.pool.get('hr.holidays')
        sequence_obj = self.pool.get('ir.sequence')
        salary_rule_pool = self.pool.get('hr.salary.rule')
        contract_obj = self.pool.get('hr.contract')
        resource_attendance_pool = self.pool.get('resource.calendar.attendance')
        if context is None:
            context = {}

        for slip in self.browse(cr, uid, ids, context=context):
            old_slip_ids = slip_line_pool.search(cr, uid, [('slip_id', '=', slip.id)], context=context)
            if old_slip_ids:
                slip_line_pool.unlink(cr, uid, old_slip_ids, context=context)
            update = {}
            ttyme = datetime.fromtimestamp(time.mktime(time.strptime(slip.date, "%Y-%m-%d")))
            contract_id = slip.contract_id.id
            if not contract_id:
                update.update({'struct_id': False})
                contracts = self.get_contract(cr, uid, slip.employee_id, slip.date, context=context)
            else:
                contracts = contract_obj.browse(cr, uid, [contract_id], context=context)
            if not contracts:
                update.update({
                    'basic_amount': 0.0,
                    'basic_before_leaves': 0.0,
                    'name': 'Salary Slip of %s for %s' % (slip.employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                    'state': 'draft',
                    'contract_id': False,
                    'struct_id': False,
                    'company_id': slip.employee_id.company_id.id
                })
                self.write(cr, uid, [slip.id], update, context=context)
                continue
            net_allow = 0.0
            net_deduct = 0.0
            all_basic = 0.0
            for contract in contracts:
                sal_structure = []
                rules = []
                all_basic += contract.wage
                if contract.struct_id.id:
                    sal_structure = self._get_parent_structure(cr, uid, [contract.struct_id.id], context=context)
                for struct in sal_structure:
                    lines = func_pool.browse(cr, uid, struct, context=context).rule_ids
                    for rl in lines:
                        if rl.child_ids:
                            for r in rl.child_ids:
                                lines.append(r)
                        rules.append(rl)
                ad = []
                total = 0.0
                obj = {'basic': contract.wage}
                for line in rules:
                    cd = line.code
                    base = line.computational_expression
                    amt = eval(base, obj)
                    if line.amount_type == 'per':
                        al = line.amount * amt
                        obj[cd] = al
                    elif line.amount_type == 'code':
                        localdict = {'basic': amt, 'employee': slip.employee_id, 'contract': contract}
                        exec line.python_compute in localdict
                        val = localdict['result']
                        obj[cd] = val
                    else:
                        obj[cd] = line.amount or 0.0

                for line in rules:
                    #Removing below condition because it stop to append child rule in payslip line and does not allow child rule to consider in calculation
#                    if line.category_id.code in ad:
#                        continue

                    ad.append(line.category_id.code)
                    cd = line.category_id.code.lower()
                    calculate = False
                    try:
                        exp = line.conditions
                        exec line.conditions in obj
                        calculate = eval(exp, obj)
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

                    if not calculate:
                        continue

                    value = 0.0
                    base = line.computational_expression
                    try:
                        amt = eval(base, obj)
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
                    if line.amount_type == 'per':
                        try:
#                            if line.child_depend == False:
                            if line.parent_rule_id:
                                for rul in [line.parent_rule_id]:
                                    val = rul.amount * amt
                                    amt = val
                            value = line.amount * amt
                            if line.condition_range_min or line.condition_range_max:
                                if ((value < line.condition_range_min) or (value > line.condition_range_max)):
                                    value = 0.0
                                else:
                                    value = value
                            else:
                                value = value
                        except Exception, e:
                            raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

                    elif line.amount_type == 'fix':
#                        if line.child_depend == False:
                        if line.parent_rule_id:
                            for rul in [line.parent_rule_id]:
                                value = value
                        if line.condition_range_min or line.condition_range_max:
                            if ((line.amount < line.condition_range_min) or (line.amount > line.condition_range_max)):
                                value = value
                            else:
                                value = line.amount
                        else:
                            value = line.amount

                    elif line.amount_type == 'code':
                        localdict = {'basic': amt, 'employee': slip.employee_id, 'contract': contract}
                        exec line.python_compute in localdict
                        val = localdict['result']
#                        if line.child_depend == False:
                        if line.parent_rule_id:
                            for rul in [line.parent_rule_id]:
                                value = val
                        if line.condition_select == 'range':
                            if line.condition_range_min or line.condition_range_max:
                                if ((line.amount < line.condition_range_min) or (line.amount > line.condition_range_max)):
                                    value = value
                                else:
                                    value = val
                        else:
                            value = val
                    if value < 0:
                        net_deduct += value
                    else:
                        net_allow += value
                    total += value
                    vals = {
                        'slip_id': slip.id,
                        'category_id': line.category_id.id,
                        'name': line.name,
                        'sequence': line.sequence,
                        'type': line.type.id,
                        'code': line.code,
                        'amount_type': line.amount_type,
                        'amount': line.amount,
                        'total': value,
                        'employee_id': slip.employee_id.id,
                        'base': line.computational_expression
                    }
                    slip_ids = slip_line_pool.search(cr, uid, [('code', '=', line.code), ('slip_id', '=', slip.id)])
                    if not slip_ids:
                        if line.appears_on_payslip:
                            if line.condition_range_min or line.condition_range_max:
                                if not ((value < line.condition_range_min) or (value > line.condition_range_max)):
                                    slip_line_pool.create(cr, uid, vals, {})
                            else:
                                slip_line_pool.create(cr, uid, vals, {})

                basic = contract.wage
                basic_before_leaves = slip.basic_amount
                working_day = 0
                off_days = 0
                dates = prev_bounds(slip.date)
                calendar_id = slip.employee_id.contract_id.working_hours.id
                if not calendar_id:
                    raise osv.except_osv(_('Error !'), _("Please define working schedule on %s's contract") % (slip.employee_id.name))
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
#                perday = working_day and basic / working_day or 0.0
                total = 0.0
                leave = 0.0
                leave_ids = self._get_leaves(cr, uid, slip.date, slip.employee_id, contract, context)
                total_leave = 0.0
                paid_leave = 0.0
                h_ids = holiday_pool.browse(cr, uid, leave_ids, context=context)
                for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
    #                if not hday.holiday_status_id.head_id:
    #                    raise osv.except_osv(_('Error !'), _('Please check configuration of %s, payroll head is missing') % (hday.holiday_status_id.name))
                    slip_lines = salary_rule_pool.search(cr, uid, [('code', '=', hday.holiday_status_id.code)], context=context)
                    if not slip_lines:
                        raise osv.except_osv(_('Error !'), _('Salary rule is not defined for %s. Please check the configuration') % (hday.holiday_status_id.name))
                    salary_rule = salary_rule_pool.browse(cr, uid, slip_lines, context=context)[0]
                    base = salary_rule.computational_expression
                    obj = {'basic': hday.contract_id.wage}
                    res = {
                        'slip_id': slip.id,
                        'name': salary_rule.name + '-%s' % (hday.number_of_days),
                        'code': salary_rule.code,
                        'amount_type': salary_rule.amount_type,
                        'category_id': salary_rule.category_id.id,
                        'sequence': salary_rule.sequence,
                        'employee_id': slip.employee_id.id,
                        'base': base
                    }
                    days = hday.number_of_days
                    if hday.number_of_days < 0:
                        days = hday.number_of_days * -1
                    total_leave += days
                    try:
                        amt = eval(base, obj)
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
                    if salary_rule.amount_type == 'per':
                        try:
    #                        if salary_rule.child_depend == False:
                            if salary_rule.parent_rule_id:
                                for rul in [salary_rule.parent_rule_id]:
                                    val = rul.amount * amt
                                    amt = val
                            value = salary_rule.amount * amt * days
                            if salary_rule.condition_select == 'range':
                                if salary_rule.condition_range_min or salary_rule.condition_range_max:
                                    if ((value < salary_rule.condition_range_min) or (value > salary_rule.condition_range_max)):
                                        value = 0.0
                                    else:
                                        value = value
                            else:
                                value = value
                        except Exception, e:
                            raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

                    elif salary_rule.amount_type == 'fix':
    #                    if salary_rule.child_depend == False:
                        if salary_rule.parent_rule_id:
                            for rul in [salary_rule.parent_rule_id]:
                                value = salary_rule.amount * days
                        elif salary_rule.condition_select == 'range':
                            if salary_rule.condition_range_min or salary_rule.condition_range_max:
                                if ((salary_rule.amount < salary_rule.condition_range_min) or (salary_rule.amount > salary_rule.condition_range_max)):
                                    value = 0.0
                                else:
                                    value = salary_rule.amount * days
                        else:
                            value = salary_rule.amount * days

                    elif salary_rule.amount_type == 'code':
                        localdict = {'basic': amt, 'employee': slip.employee_id, 'contract': contract}
                        exec salary_rule.python_compute in localdict
                        val = localdict['result'] * days
    #                    if salary_rule.child_depend == False:
                        if salary_rule.parent_rule_id:
                            for rul in [salary_rule.parent_rule_id]:
                                value = val
                        if salary_rule.condition_select == 'range':
                            if salary_rule.condition_range_min or salary_rule.condition_range_max:
                                if ((salary_rule.amount < salary_rule.condition_range_min) or (salary_rule.amount > salary_rule.condition_range_max)):
                                    value = value
                                else:
                                    value = val
                        else:
                            value = val
                    if value < 0:
                        net_deduct += value
                    else:
                        net_allow += value
                    res['amount'] = salary_rule.amount
                    res['type'] = salary_rule.type.id
                    leave += days
                    total += value
                    res['total'] = value
                    if salary_rule.appears_on_payslip:
                        if salary_rule.condition_range_min or salary_rule.condition_range_max:
                            if not ((value < salary_rule.condition_range_min) or (value > salary_rule.condition_range_max)):
                                slip_line_pool.create(cr, uid, res, context=context)
                        else:
                            slip_line_pool.create(cr, uid, res, context=context)

                holiday_pool.write(cr, uid, leave_ids, {'payslip_id': slip.id}, context=context)
                basic = basic - total

            net_id = salary_rule_pool.search(cr, uid, [('code', '=', 'NET')])
            for line in salary_rule_pool.browse(cr, uid, net_id, context=context):
                dic = {'basic': all_basic, 'allowance': net_allow, 'deduction': net_deduct}
                exec line.python_compute in dic
                tot = dic['total']
                vals = {
                    'slip_id': slip.id,
                    'category_id': line.category_id.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'type': line.type.id,
                    'code': line.code,
                    'amount_type': line.amount_type,
                    'amount': line.amount,
                    'total': tot,
                    'employee_id': slip.employee_id.id,
                    'base': line.computational_expression
                }
            slip_line_pool.create(cr, uid, vals, context=context)
            number = sequence_obj.get(cr, uid, 'salary.slip')
            update.update({
                'number': number,
                'name': 'Salary Slip of %s for %s' % (slip.employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                'basic_amount': basic_before_leaves,
                'basic_before_leaves': basic_before_leaves,
                'total_pay': basic + total,
                'leaves': total,
                'state':'draft',
                'holiday_days': leave,
                'worked_days': working_day - leave,
                'working_days': working_day,
                'company_id': slip.employee_id.company_id.id
            })
        return self.write(cr, uid, [slip.id], update, context=context)

    def onchange_employee_id(self, cr, uid, ids, ddate, employee_id=False, contract_id=False, context=None):
        func_pool = self.pool.get('hr.payroll.structure')
        slip_line_pool = self.pool.get('hr.payslip.line')
        salary_rule_pool = self.pool.get('hr.salary.rule')
        holiday_pool = self.pool.get('hr.holidays')
        sequence_obj = self.pool.get('ir.sequence')
        empolyee_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        resource_attendance_pool = self.pool.get('resource.calendar.attendance')

        if context is None:
            context = {}

        old_slip_ids = ids and slip_line_pool.search(cr, uid, [('slip_id', '=', ids[0])], context=context) or False
        if old_slip_ids:
            slip_line_pool.unlink(cr, uid, old_slip_ids, context=context)

        update = {'value':{'line_ids':[], 'holiday_ids':[], 'details_by_salary_head':[], 'name':'', 'working_days': 0.0, 'holiday_days': 0.0, 'worked_days': 0.0, 'basic_before_leaves': 0.0, 'basic_amount': 0.0, 'leaves': 0.0, 'total_pay': 0.0}}
        if not employee_id:
            update['value'].update({'contract_id': False, 'struct_id': False})
            return update
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(ddate, "%Y-%m-%d")))

        if employee_id and not context.get('contract', False):
            employee_id = empolyee_obj.browse(cr, uid, employee_id, context=context)
            contracts = self.get_contract(cr, uid, employee_id, ddate, context=context)
            if not contracts:
                update['value'].update({
                    'basic_amount': 0.0,
                    'basic_before_leaves': 0.0,
                    'name':'Salary Slip of %s for %s' % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                    'contract_id': False,
                    'struct_id': False,
                    'company_id': employee_id.company_id.id
                })
                return update
            contracts = [contracts[0]]
            update['value'].update({
                    'struct_id': contracts[0].struct_id.id,
                    'contract_id': contracts[0].id
            })
        if context.get('contract', False):
            if contract_id:
                employee_id = empolyee_obj.browse(cr, uid, employee_id, context=context)
                contracts = [contract_obj.browse(cr, uid, contract_id, context=context)]
                update['value'].update({'struct_id': contracts[0].struct_id.id})
            else: # ?
                employee_id = empolyee_obj.browse(cr, uid, employee_id, context=context)
                contracts = self.get_contract(cr, uid, employee_id, ddate, context=context)
                if not contracts:
                    update['value'].update({
                        'basic_amount': 0.0,
                        'basic_before_leaves': 0.0,
                        'name':'Salary Slip of %s for %s' % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                        'contract_id': False,
                        'struct_id': False,
                        'company_id': employee_id.company_id.id
                    })
                    return update
                update['value'].update({'contract_id': False, 'struct_id': False})

        final_total = 0.0
        all_basic = 0.0
        net_allow = 0.0
        net_deduct = 0.0
        for contract in contracts:
            lines = []
            rules = []
            sal_structure = []
            all_basic += contract.wage
            if contract.struct_id.id:
                sal_structure = self._get_parent_structure(cr, uid, [contract.struct_id.id], context=context)
            for struct in sal_structure:
                lines = func_pool.browse(cr, uid, struct, context=context).rule_ids
                for rl in lines:
                    if rl.child_ids:
                        for r in rl.child_ids:
                            lines.append(r)
                    rules.append(rl)
            ad = []
            total = 0.0
            obj = {'basic': contract.wage}
            for line in rules:
                cd = line.code
                base = line.computational_expression
                amt = eval(base, obj)
                if line.amount_type == 'per':
                    al = line.amount * amt
                    obj[cd] = al
                elif line.amount_type=='code':
                    localdict = {'basic':amt, 'employee':employee_id, 'contract':contract}
                    exec line.python_compute in localdict
                    val = localdict['result']
                    obj[cd] = val
                else:
                    obj[cd] = line.amount or 0.0

            for line in rules:

                #Removing below condition because it stop to append child rule in payslip line and does not allow child rule to consider in calculation
#                if line.category_id.code in ad:
#                    continue

                ad.append(line.category_id.code)
                cd = line.category_id.code.lower()
                calculate = False
                try:
                    exp = line.conditions
                    exec line.conditions in obj
                    calculate = eval(exp, obj)
                except Exception, e:
                    raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

                if not calculate:
                    continue

                value = 0.0
                base = line.computational_expression
                try:
                    amt = eval(base, obj)
                except Exception, e:
                    raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
                if line.amount_type == 'per':
                    try:
#                        if line.child_depend == False:
                        if line.parent_rule_id:
                            for rul in [line.parent_rule_id]:
                                val = rul.amount * amt
                                amt = val
                        value = line.amount * amt
                        if line.condition_select == 'range':
                            if line.condition_range_min or line.condition_range_max:
                                if ((value < line.condition_range_min) or (value > line.condition_range_max)):
                                    value = 0.0
                                else:
                                    value = value
                        else:
                            value = value
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

                elif line.amount_type == 'fix':
#                    if line.child_depend == False:
                    if line.parent_rule_id:
                        for rul in [line.parent_rule_id]:
                            value = value
                    if line.condition_select == 'range':
                        if line.condition_range_min or line.condition_range_max:
                            if ((line.amount < line.condition_range_min) or (line.amount > line.condition_range_max)):
                                value = value
                            else:
                                value = line.amount
                    else:
                            value = line.amount

                elif line.amount_type=='code':
                    localdict = {'basic':amt, 'employee':employee_id, 'contract':contract}
                    exec line.python_compute in localdict
                    val = localdict['result']
#                    if line.child_depend == False:
                    if line.parent_rule_id:
                        for rul in [line.parent_rule_id]:
                            value = val
                    if line.condition_select == 'range':
                        if line.condition_range_min or line.condition_range_max:
                            if ((line.amount < line.condition_range_min) or (line.amount > line.condition_range_max)):
                                value = value
                            else:
                                value = val
                    else:
                        value = val
                if value < 0:
                    net_deduct += value
                else:
                    net_allow += value
                total += value
                vals = {
                    'category_id': line.category_id.id,
                    'name': line.name,
                    'sequence': line.sequence,
                    'type': line.type.id,
                    'code': line.code,
                    'amount_type': line.amount_type,
                    'amount': line.amount,
                    'total': value,
                    'employee_id': employee_id.id,
                    'base': line.computational_expression
                }
                if vals not in update['value']['line_ids']:
                    if line.appears_on_payslip:
                        if line.condition_range_min or line.condition_range_max:
                            if not ((value < line.condition_range_min) or (value > line.condition_range_max)):
                                update['value']['line_ids'].append(vals)
                        else:
                            update['value']['line_ids'].append(vals)

                basic = contract.wage
                final_total += basic + total
#            number = sequence_obj.get(cr, uid, 'salary.slip')
#            update['value'].update({
#    #            'struct_id': function,
#                'number': number,
#                'basic_amount': all_basic,
#                'basic_before_leaves': basic,
#                'total_pay': final_total,
#                'name': 'Salary Slip of %s for %s' % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#    #            'contract_id': contract.id,
#                'company_id': employee_id.company_id.id
#            })

            basic_before_leaves = update['value']['basic_amount']
            total_before_leaves = update['value']['total_pay']
            working_day = 0
            off_days = 0
            dates = prev_bounds(ddate)
            calendar_id = contract.working_hours.id
            if not calendar_id:
                raise osv.except_osv(_('Error !'), _("Please define working schedule on %s's %s contract") % (employee_id.name, contract.name))
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
    #        perday = working_day and basic / working_day or 0.0
            total = 0.0
            leave = 0.0
            leave_ids = self._get_leaves(cr, uid, ddate, employee_id, contract, context)
            total_leave = 0.0
            paid_leave = 0.0

            for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
    #            if not hday.holiday_status_id.code:
    #                raise osv.except_osv(_('Error !'), _('Please check configuration of %s, code is missing') % (hday.holiday_status_id.name))
                slip_lines = salary_rule_pool.search(cr, uid, [('code','=',hday.holiday_status_id.code)], context=context)
                head_sequence = 0
                if not slip_lines:
                    raise osv.except_osv(_('Error !'), _('Salary rule is not defined for %s. Please check the configuration') % (hday.holiday_status_id.name))
                hd_rule = salary_rule_pool.browse(cr, uid, slip_lines, context=context)[0]
                leave_rule = []
                leave_rule.append(hd_rule)
                if hd_rule.child_ids:
                    leave_rule.append((hd_rule.child_ids[0]))
                obj = {'basic': hday.contract_id.wage}
                for salary_rule in leave_rule:
                    base = salary_rule.computational_expression
                    res = {
                        'name': salary_rule.name + '-%s' % (hday.number_of_days),
                        'code': salary_rule.code,
                        'amount_type': salary_rule.amount_type,
                        'category_id': salary_rule.category_id.id,
                        'sequence': salary_rule.sequence,
                        'employee_id': employee_id.id,
                        'base': base
                    }
                    days = hday.number_of_days
                    if hday.number_of_days < 0:
                        days = hday.number_of_days * -1
                    total_leave += days
                    try:
                        amt = eval(base, obj)
                    except Exception, e:
                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
                    if salary_rule.amount_type == 'per':
                        try:
    #                        if salary_rule.child_depend == False:
                            if salary_rule.parent_rule_id:
                                for rul in [salary_rule.parent_rule_id]:
                                    val = rul.amount * amt
                                    amt = val
                            value = salary_rule.amount * amt * days
                            if salary_rule.condition_select == 'range':
                                if salary_rule.condition_range_min or salary_rule.condition_range_max:
                                    if ((value < salary_rule.condition_range_min) or (value > salary_rule.condition_range_max)):
                                        value = 0.0
                                    else:
                                        value = value
                            else:
                                value = value
                        except Exception, e:
                            raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))

                    elif salary_rule.amount_type == 'fix':
    #                    if salary_rule.child_depend == False:
                        if salary_rule.parent_rule_id:
                            for rul in [salary_rule.parent_rule_id]:
                                value = salary_rule.amount * days
                        if salary_rule.condition_select == 'range':
                            if salary_rule.condition_range_min or salary_rule.condition_range_max:
                                if ((salary_rule.amount < salary_rule.condition_range_min) or (salary_rule.amount > salary_rule.condition_range_max)):
                                    value = 0.0
                                else:
                                    value = salary_rule.amount * days
                        else:
                            value = salary_rule.amount * days

                    elif salary_rule.amount_type=='code':
                        localdict = {'basic':amt, 'employee':employee_id, 'contract':contract_id}
                        exec salary_rule.python_compute in localdict
                        val = localdict['result'] * days
    #                    if salary_rule.child_depend == False:
                        if salary_rule.parent_rule_id:
                            for rul in [salary_rule.parent_rule_id]:
                                value = val
                        if salary_rule.condition_select == 'range':
                            if salary_rule.condition_range_min or salary_rule.condition_range_max:
                                if ((salary_rule.amount < salary_rule.condition_range_min) or (salary_rule.amount > salary_rule.condition_range_max)):
                                    value = value
                                else:
                                    value = val
                        else:
                            value = val
                    if value < 0:
                        net_deduct += value
                    else:
                        net_allow += value
                    res['amount'] = salary_rule.amount
                    res['type'] = salary_rule.type.id
                    leave += days
                    total += value
                    res['total'] = value
                    if salary_rule.appears_on_payslip:
                        if salary_rule.condition_range_min or salary_rule.condition_range_max:
                            if not ((value < salary_rule.condition_range_min) or (value > salary_rule.condition_range_max)):
                                update['value']['line_ids'].append(res)
                        else:
                            update['value']['line_ids'].append(res)

        net_id = salary_rule_pool.search(cr, uid, [('code', '=', 'NET')])
        for line in salary_rule_pool.browse(cr, uid, net_id, context=context):
            dic = {'basic': all_basic, 'allowance': net_allow, 'deduction': net_deduct}
            exec line.python_compute in dic
            tot = dic['total']
            vals = {
                'category_id': line.category_id.id,
                'name': line.name,
                'sequence': line.sequence,
                'type': line.type.id,
                'code': line.code,
                'amount_type': line.amount_type,
                'amount': line.amount,
                'total': tot,
                'employee_id': employee_id.id,
                'base': line.computational_expression
            }
            update['value']['line_ids'].append(vals)

        number = sequence_obj.get(cr, uid, 'salary.slip')
        update['value'].update({
            'number': number,
            'name': 'Salary Slip of %s for %s' % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#            'basic_amount': basic, # no need to pass its related field... but for multi contract we need to check for the possibility ...
            'basic_before_leaves': basic_before_leaves,
            'total_pay': total_before_leaves + total,
            'leaves': total,
            'holiday_days': leave,
            'worked_days': working_day - leave,
            'working_days': working_day,
            'company_id': employee_id.company_id.id
        })
        return update

    def onchange_contract_id(self, cr, uid, ids, date, employee_id=False, contract_id=False, context=None):
        if context is None:
            context = {}
        res = {'value':{'line_ids':[], 'holiday_ids':[], 'details_by_salary_head':[], 'name':'', 'working_days': 0.0, 'holiday_days': 0.0, 'worked_days': 0.0, 'basic_before_leaves': 0.0, 'basic_amount': 0.0, 'leaves': 0.0, 'total_pay': 0.0}}
        context.update({'contract': True})
        if not contract_id:
            res['value'].update({'struct_id': False})
        return self.onchange_employee_id(cr, uid, ids, ddate=date, employee_id=employee_id, contract_id=contract_id, context=context)

hr_payslip()

class hr_holidays(osv.osv):

    _inherit = "hr.holidays"
    _columns = {
        'payslip_id': fields.many2one('hr.payslip', 'Payslip'),
        'contract_id': fields.many2one('hr.contract', 'Contract', readonly=True, states={'draft':[('readonly',False)]})
    }

    def onchange_employee_id(self, cr, uid, ids, employee_id=False, date_from=False, context=None):
        if not employee_id:
            return {}
        contract_obj = self.pool.get('hr.contract')
        res = {}
        employee_id = self.pool.get('hr.employee').browse(cr, uid, employee_id, context)

        # fix me: Date_from is not comming in onchange..
        contract_ids = self.pool.get('hr.payslip').get_contract(cr, uid, employee_id, date_from, context=context)
        res.update({
            'contract_id': contract_ids and contract_ids[0].id or False,
        })
        return {'value': res}

#    def holidays_confirm(self, cr, uid, ids, *args):
#        leaves = self.browse(cr, uid, ids)
#        for leave in leaves:
#            if not leave.contract_id and leave.type == 'remove':
#                raise osv.except_osv(_('Warning !'), _("Please define contract on %s's leave request ! ") % (leave.employee_id.name))
#        return super(hr_holidays, self).holidays_confirm(cr, uid, ids, args)

hr_holidays()

class hr_payslip_line(osv.osv):
    '''
    Payslip Line
    '''

    _name = 'hr.payslip.line'
    _description = 'Payslip Line'

    def onchange_category(self, cr, uid, ids, category_id=False):
        if not category_id:
            return {}
        res = {}
        category = self.pool.get('hr.salary.head').browse(cr, uid, category_id)
        res.update({
            'name': category.name,
            'code': category.code,
            'type': category.type.id
        })
        return {'value': res}

    def onchange_amount(self, cr, uid, ids, amount, typ):
        if typ and typ == 'per':
            if int(amount) > 0:
                amount = amount / 100
        return {'value': {'amount': amount}}

    _columns = {
        'slip_id':fields.many2one('hr.payslip', 'Pay Slip', required=False),#FIXME: required = TRUE.We cannot make it to True because while creating salary rule(which is inherited from hr.payslip.line),we cannot have slip_id.
#        'function_id':fields.many2one('hr.payroll.structure', 'Function', required=False),#FIXME: function?should be struct_id or payroll_structure_id..We have rule_ids(many2many) on hr.payroll.structure,so this field is not required here.
        'employee_id':fields.many2one('hr.employee', 'Employee', required=False),#FIXME: required = TRUE.We cannot make it to True because while creating salary rule(which is inherited from hr.payslip.line),we cannot have employee_id.
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'base':fields.char('Formula', size=1024, required=False, readonly=False),
        'code':fields.char('Code', size=64, required=False, readonly=False),
        'category_id':fields.many2one('hr.salary.head', 'Salary Head', required=True),
        'type':fields.related('category_id', 'type', relation='hr.salary.head.type', string='Salary Head Type', type='many2one', store=True), #many2one('hr.salary.head.type', 'Type', required=True, help="Used for the reporting purpose."),
        'amount_type':fields.selection([
            ('per','Percentage (%)'),
            ('fix','Fixed Amount'),
            ('code','Python Code'),
        ],'Amount Type', select=True, required=True, help="The computation method for the rule amount."),
        'amount': fields.float('Amount / Percentage', digits_compute=dp.get_precision('Account'), help="For rule of type percentage, enter % ratio between 0-1."),
        'total': fields.float('Sub Total', digits_compute=dp.get_precision('Account')),
        'company_contrib': fields.float('Company Contribution', readonly=True, digits_compute=dp.get_precision('Account')),
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence'),
        'note':fields.text('Description'),
    }
    _order = 'sequence'
    _defaults = {
        'amount_type': 'per',
        'amount': 0.0,
    }

hr_payslip_line()

class hr_salary_rule(osv.osv):

    _inherit = 'hr.payslip.line'
    _name = 'hr.salary.rule'
    _columns = {
        'appears_on_payslip': fields.boolean('Appears on Payslip', help="Used for the display of rule on payslip"),
        'condition_range_min': fields.float('Minimum Range', required=False, help="The minimum amount, applied for this rule."),
        'condition_range_max': fields.float('Maximum Range', required=False, help="The maximum amount, applied for this rule."),
        'parent_rule_id':fields.many2one('hr.salary.rule', 'Parent Salary Rule', select=True),
        'child_depend':fields.boolean('Children Rule'),
        'child_ids':fields.one2many('hr.salary.rule', 'parent_rule_id', 'Child Salary Rule'),
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
        'condition_select': fields.selection([('range', 'Range'), ('python', 'Python Expression')], "Condition based on"),
        'computational_expression':fields.char('Computational Expression',size=1024, required=True, readonly=False, help='This will use to computer the % fields values, in general its on basic, but You can use all heads code field in small letter as a variable name i.e. hra, ma, lta, etc...., also you can use, static varible basic'),
        'conditions':fields.char('Condition', size=1024, required=True, readonly=False, help='Applied this rule for calculation if condition is true.You can specify condition like basic > 1000.'),
        'active':fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the salary rule without removing it."),
        'python_compute':fields.text('Python Code'),
        'display_child_rules': fields.boolean('Display Child Rules', help="Used for the display of Child Rules on payslip"),
        'company_contribution':fields.boolean('Company Contribution',help="This rule has Company Contributions."),
        'expression_result':fields.char('Expression based on',size=1024, required=False, readonly=False, help='result will be affected to a variable'),
        'parent_rule_id':fields.many2one('hr.salary.rule', 'Parent Salary Rule', select=True),
     }

    _defaults = {
        'python_compute': '''# basic\n# employee: hr.employee object or None\n# contract: hr.contract object or None\n\nresult = basic * 0.10''',
        'conditions': 'True',
        'computational_expression': 'basic',
        'sequence': 5,
        'appears_on_payslip': True,
        'active': True,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'condition_select': 'python',
     }

    def onchange_company(self, cr, uid, ids, company_contribution=False, context=None):
        if company_contribution:
            return {'value': {'appears_on_payslip': False}}
        return {'value': {}}

#    def _execute_function(self, cr, uid, id, value, context=None):
#        """
#        self: pointer to self object
#        cr: cursor to database
#        uid: user id of current executer
#        """
#        line_pool = self.pool.get('company.contribution.line')
#        res = 0
#        ids = line_pool.search(cr, uid, [('category_id','=',id), ('to_val','>=',value),('from_val','<=',value)], context=context)
#        if not ids:
#            ids = line_pool.search(cr, uid, [('category_id','=',id), ('from','<=',value)], context=context)
#        if not ids:
#            res = 0
#        else:
#            res = line_pool.browse(cr, uid, ids, context=context)[0].value
#        return res
#
#    def compute(self, cr, uid, id, value, context=None):
#        contrib = self.browse(cr, uid, id, context=context)
#        if contrib.amount_type == 'fix':
#            return contrib.contribute_per
#        elif contrib.amount_type == 'per':
#            return value * contrib.contribute_per
#        elif contrib.amount_type == 'func':
#            return self._execute_function(cr, uid, id, value, context)
#        return 0.0
#
hr_salary_rule()

class hr_payroll_structure(osv.osv):

    _inherit = 'hr.payroll.structure'
    _columns = {
        'rule_ids':fields.many2many('hr.salary.rule', 'hr_structure_salary_rule_rel', 'struct_id', 'rule_id', 'Salary Rules'),
    }

hr_payroll_structure()

class hr_employee(osv.osv):
    '''
    Employee
    '''

    _inherit = 'hr.employee'
    _description = 'Employee'

    def _calculate_basic(self, cr, uid, ids, name, args, context):
        if not ids: return {}
        res = {}
        current_date = datetime.now().strftime('%Y-%m-%d')
        for employee in self.browse(cr, uid, ids, context=context):
            if not employee.contract_ids:
                res[employee.id] = {'basic': 0.0}
                continue
            cr.execute( 'SELECT SUM(wage) '\
                        'FROM hr_contract '\
                        'WHERE employee_id = %s '\
                        'AND date_start <= %s '\
                        'AND (date_end > %s OR date_end is NULL)',
                         (employee.id, current_date, current_date))
            result = dict(cr.dictfetchone())
            res[employee.id] = {'basic': result['sum']}
        return res

    _columns = {
#        'line_ids':fields.one2many('hr.payslip.line', 'employee_id', 'Salary Structure', required=False),
        'slip_ids':fields.one2many('hr.payslip', 'employee_id', 'Payslips', required=False, readonly=True),
        'basic': fields.function(_calculate_basic, method=True, multi='dc', type='float', string='Basic Salary', digits_compute=dp.get_precision('Account'), help="Sum of all current contract's wage of employee."),
    }

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
