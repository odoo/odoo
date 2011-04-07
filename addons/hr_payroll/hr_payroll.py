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
from dateutil import relativedelta

import netsvc
from osv import fields, osv
import tools
from tools.translate import _
import decimal_precision as dp

from tools.safe_eval import safe_eval as eval

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
        'code':fields.char('Reference', size=64, required=True),
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

    def get_all_rules(self, cr, uid, structure_ids, context=None):
        """
        @param structure_ids: list of structure
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """
        def recursive_search_of_rule(rule_ids):
            children_rules = []
            for rule in rule_ids:
                if rule.child_ids:
                    children_rules += recursive_search_of_rule(rule.child_ids)
            return [(r.id, r.sequence) for r in rule_ids] + children_rules

        all_rules = []
        for struct in self.browse(cr, uid, structure_ids, context=context):
            all_rules += recursive_search_of_rule(struct.rule_ids)
        return all_rules

    def _get_parent_structure(self, cr, uid, struct_ids, context=None):
        if not struct_ids:
            return []
        parent = []
        for struct in self.browse(cr, uid, struct_ids, context=context):
            if struct.parent_id:
                parent.append(struct.parent_id.id)
        if parent:
            parent = self._get_parent_structure(cr, uid, parent, context)
        return parent + struct_ids

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

    def get_all_structures(self, cr, uid, contract_ids, context=None):
        """
        @param contract_ids: list of contracts
        @return: the structures linked to the given contracts, ordered by hierachy (parent=False first, then first level children and so on) and without duplicata
        """
        all_structures = []
        structure_ids = [contract.struct_id.id for contract in self.browse(cr, uid, contract_ids, context=context)]
        return list(set(self.pool.get('hr.payroll.structure')._get_parent_structure(cr, uid, structure_ids, context=context)))

hr_contract()

class contrib_register(osv.osv):
    '''
    Contribution Register
    '''

    _name = 'hr.contibution.register'
    _description = 'Contribution Register'

    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'register_line_ids':fields.one2many('hr.payslip.line', 'register_id', 'Register Line', readonly=True),
        'note': fields.text('Description'),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }

contrib_register()

class hr_salary_head(osv.osv):
    """
    HR Salary Head
    """

    _name = 'hr.salary.head'
    _description = 'Salary Head'
    _columns = {
        'name':fields.char('Name', size=64, required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, readonly=False),
        'parent_id':fields.many2one('hr.salary.head', 'Parent', help="Linking a salary head to its parent is used only for the reporting purpose."),
        'note': fields.text('Description'),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'sequence': fields.integer('Sequence', required=True, help='Display sequence order'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'sequence': 5
    }

hr_salary_head()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''

    _name = 'hr.payslip'
    _description = 'Pay Slip'

#TODO unused for now, cause the field is commented but we want to put it back
#    def _get_salary_rules(self, cr, uid, ids, field_names, arg=None, context=None):
#        structure_obj = self.pool.get('hr.payroll.structure')
#        contract_obj = self.pool.get('hr.contract')
#        res = {}
#        rules = []
#        contracts = []
#        structures = []
#        rule_ids = []
#        sorted_salary_heads = []
#        for record in self.browse(cr, uid, ids, context=context):
#            if record.contract_id:
#                contracts.append(record.contract_id.id)
#            else:
#                contracts = self.get_contract(cr, uid, record.employee_id, record.date, context=context)
#            for contract in contracts:
#                structures = contract_obj.get_all_structures(cr, uid, [contract], context)
#            res[record.id] = {}
#            for struct in structures:
#                rule_ids = structure_obj.get_all_rules(cr, uid, [struct], context=None)
#                for rl in rule_ids:
#                    if rl[0] not in rules:
#                        rules.append(rl[0])
#            cr.execute('''SELECT sr.id FROM hr_salary_rule as sr, hr_salary_head as sh
#               WHERE sr.category_id = sh.id AND sr.id in %s ORDER BY sh.sequence''',(tuple(rules),))
#            for x in cr.fetchall():
#                sorted_salary_heads.append(x[0])
#            for fn in field_names:
#               if fn == 'details_by_salary_head':
#                   res[record.id] = {fn: sorted_salary_heads}
#        return res

    _columns = {
        'struct_id': fields.many2one('hr.payroll.structure', 'Structure', help='Defines the rules that have to be applied to this payslip, accordingly to the contract chosen. If you let empty the field contract, this field isn\'t mandatory anymore and thus the rules applied will be all the rules set on the structure of all contracts of the employee valid for the chosen period'),
        'name': fields.char('Description', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'number': fields.char('Reference', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_from': fields.date('Date From', readonly=True, states={'draft': [('readonly', False)]}, required=True),
        'date_to': fields.date('Date To', readonly=True, states={'draft': [('readonly', False)]}, required=True),
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
        'line_ids': fields.one2many('hr.payslip.line', 'slip_id', 'Payslip Line', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'input_line_ids': fields.one2many('hr.payslip.input', 'payslip_id', 'Payslip Inputs', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'paid': fields.boolean('Made Payment Order ? ', required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'note': fields.text('Description'),
        'contract_id': fields.many2one('hr.contract', 'Contract', required=False, readonly=True, states={'draft': [('readonly', False)]}),
       #TODO put me back
       # 'details_by_salary_head': fields.function(_get_salary_rules, method=True, type='one2many', relation='hr.salary.rule', string='Details by Salary Head', multi='details_by_salary_head'),
    }
    _defaults = {
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
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
         #TODO clean me: this function should create the register lines accordingly to the rules computed (run the compute_sheet first)
#        holiday_pool = self.pool.get('hr.holidays')
#        salary_rule_pool = self.pool.get('hr.salary.rule')
#        structure_pool = self.pool.get('hr.payroll.structure')
#        register_line_pool = self.pool.get('hr.contibution.register.line')
#        contracts = []
#        structures = []
#        rules = []
#        lines = []
#        sal_structures =[]
#        for slip in self.browse(cr, uid, ids, context=context):
#            if slip.contract_id:
#                contracts.append(slip.contract_id)
#            else:
#                contracts = self.get_contract(cr, uid, slip.employee_id, slip.date, context=context)
#            for contract in contracts:
#                structures.append(contract.struct_id.id)
#                leave_ids = self._get_leaves(cr, uid, slip.date, slip.employee_id, contract, context)
#                for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
#                    salary_rules = salary_rule_pool.search(cr, uid, [('code', '=', hday.holiday_status_id.code)], context=context)
#                    rules +=  salary_rule_pool.browse(cr, uid, salary_rules, context=context)
#            for structure in structures:
#                sal_structures = self._get_parent_structure(cr, uid, [structure], context=context)
#                for struct in sal_structures:
#                    lines = structure_pool.browse(cr, uid, struct, context=context).rule_ids
#                    for line in lines:
#                        if line.child_ids:
#                            for r in line.child_ids:
#                                lines.append(r)
#                        rules.append(line)
#            base = {
#                'basic': slip.basic_amount,
#            }
#            if rules:
#                for rule in rules:
#                    if rule.company_contribution:
#                        base[rule.code.lower()] = rule.amount
#                        if rule.register_id:
#                            for slip in slip.line_ids:
#                                if slip.category_id == rule.category_id:
#                                    line_tot = slip.total
#                            value = eval(rule.computational_expression, base)
#                            company_contrib = self._compute(cr, uid, rule.id, value, employee, contract, context)
#                            reg_line = {
#                                'name': rule.name,
#                                'register_id': rule.register_id.id,
#                                'code': rule.code,
#                                'employee_id': slip.employee_id.id,
#                                'emp_deduction': line_tot,
#                                'comp_deduction': company_contrib,
#                                'total': rule.amount + line_tot
#                            }
#                            register_line_pool.create(cr, uid, reg_line, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'}, context=context)

    #TODO move this function into hr_contract module, on hr.employee object
    def get_contract(self, cr, uid, employee, date_from, date_to, context=None):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.pool.get('hr.contract')
        clause = []
        #a contract is valid if it ends between the given dates
        clause_1 = ['&',('date_end', '<=', date_to),('date_end','>=', date_from)]
        #OR if it starts between the given dates
        clause_2 = ['&',('date_start', '<=', date_to),('date_start','>=', date_from)]
        #OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = [('date_start','<=', date_from),'|',('date_end', '=', False),('date_end','>=', date)]
        clause_final =  [('employee_id', '=', employee.id),'|','|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(cr, uid, [('employee_id', '=', employee.id),], context=context)
        return contract_ids

    def compute_sheet(self, cr, uid, ids, context=None):
        slip_line_pool = self.pool.get('hr.payslip.line')
        for payslip in self.browse(cr, uid, ids, context=context):
            #delete old payslip lines
            old_slipline_ids = slip_line_pool.search(cr, uid, [('slip_id', '=', payslip.id)], context=context)
            old_slipline_ids
            if old_slipline_ids:
                slip_line_pool.unlink(cr, uid, old_slipline_ids, context=context)
            if payslip.contract_id:
                #set the list of contract for which the rules have to be applied
                contract_ids = [payslip.contract_id.id]
            else:
                #if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, payslip.employee_id, payslip.date_from, payslip.date_to, context=context)
            lines = [(0,0,line) for line in self.pool.get('hr.payslip').get_payslip_lines(cr, uid, contract_ids, payslip.id, context=context)]
            self.write(cr, uid, [payslip.id], {'line_ids': lines}, context=context)
        return True

    def get_input_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
        """
        @param contract_ids: list of contract id
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        def was_on_leave(employee_id, datetime_day, context=None):
            res = False
            day = datetime_day.strftime("%Y-%m-%d")
            holiday_ids = self.pool.get('hr.holidays').search(cr, uid, [('state','=','validate'),('employee_id','=',employee_id),('type','=','remove'),('date_from','<=',day),('date_to','>=',day)])
            if holiday_ids:
                res = self.pool.get('hr.holidays').browse(cr, uid, holiday_ids, context=context)[0].holiday_status_id.name
            return res

        res = []
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            if not contract.working_hours:
                #fill only if the contract as a working schedule linked
                continue
            attendances = {
                 'name': _("Normal Working Days paid at 100%"),
                 'sequence': 1,
                 'code': 'WORK100',
                 'number_of_days': 0.0,
                 'number_of_hours': 0.0,
                 'contract_id': contract.id,
            }
            leaves = {}
            day_from = datetime.strptime(date_from,"%Y-%m-%d")
            day_to = datetime.strptime(date_to,"%Y-%m-%d")
            nb_of_days = (day_to - day_from).days + 1
            for day in range(0, nb_of_days):
                working_hours_on_day = self.pool.get('resource.calendar').working_hours_on_day(cr, uid, contract.working_hours, day_from + timedelta(days=day), context)
                if working_hours_on_day:
                    #the employee had to work
                    leave_type = was_on_leave(contract.employee_id.id, day_from + timedelta(days=day), context=context)
                    if leave_type:
                        #if he was on leave, fill the leaves dict
                        if leave_type in leaves:
                            leaves[leave_type]['number_of_days'] += 1.0
                            leaves[leave_type]['number_of_hours'] += working_hours_on_day
                        else:
                            leaves[leave_type] = {
                                'name': leave_type,
                                'sequence': 5,
                                'code': leave_type,
                                'number_of_days': 1.0,
                                'number_of_hours': working_hours_on_day,
                                'contract_id': contract.id,
                            }
                    else:
                        #add the input vals to tmp (increment if existing)
                        attendances['number_of_days'] += 1.0
                        attendances['number_of_hours'] += working_hours_on_day
            leaves = [value for key,value in leaves.items()]
            res += [attendances] + leaves
        return res

    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        result = []
        payslip = self.pool.get('hr.payslip').browse(cr, uid, payslip_id, context=context)
        localdict = {'rules': {}, 'heads': {}, 'payslip': payslip}
        #get the ids of the structures on the contracts and their parent id as well
        structure_ids = self.pool.get('hr.contract').get_all_structures(cr, uid, contract_ids, context=context)
        #get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        #run the rules by sequence
        #import pdb;pdb.set_trace()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]

        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            employee = contract.employee_id
            localdict.update({'employee': employee, 'contract': contract})
            for rule in self.pool.get('hr.salary.rule').browse(cr, uid, sorted_rule_ids, context=context):
                #check if the rule can be applied
                if self.pool.get('hr.salary.rule').satisfy_condition(cr, uid, rule.id, localdict, context=context):
                    amount = self.pool.get('hr.salary.rule').compute_rule(cr, uid, rule.id, localdict, context=context)
                    #set/overwrite the amount computed for this rule in the localdict
                    localdict['rules'][rule.code] = amount
                    #sum the amount for its salary head
                    localdict['heads'][rule.category_id.code] = rule.category_id.code in localdict['heads'] and localdict['heads'][rule.category_id.code] + amount or amount
                    vals = {
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'total': amount,
                        'employee_id': contract.employee_id.id,
                    }
                    result.append(vals)
        return result

    def onchange_employee_id(self, cr, uid, ids, date_from, date_to, employee_id=False, contract_id=False, context=None):
        empolyee_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        input_obj = self.pool.get('hr.payslip.input')

        if context is None:
            context = {}
        #delete old input lines
        old_input_ids = ids and input_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_input_ids:
            input_obj.unlink(cr, uid, old_input_ids, context=context)

        #defaults
        res = {'value':{
                      'line_ids':[],
                      #'details_by_salary_head':[], TODO put me back
                      'name':'',
                      'contract_id': False,
                      'struct_id': False,
                      }
                 }
        if not employee_id:
            return res
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        employee_id = empolyee_obj.browse(cr, uid, employee_id, context=context)
        res['value'].update({
                           'name': _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
                           'company_id': employee_id.company_id.id
                           })

        if not context.get('contract', False):
            #fill with the first contract of the employee
            contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
            res['value'].update({
                    'struct_id': contract_ids and contract_obj.read(cr, uid, contract_ids[0], ['struct_id'], context=context)['struct_id'][0] or False,
                    'contract_id': contract_ids and contract_ids[0] or False,
            })
        else:
            if contract_id:
                #set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
                #fill the structure with the one on the selected contract
                contract_record = contract_obj.browse(cr, uid, contract_id, context=context)
                res['value'].update({'struct_id': contract_record.struct_id.id, 'contract_id': contract_id})
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
                if not contract_ids:
                    return res

        #computation of the salary input
        input_line_ids = self.get_input_lines(cr, uid, contract_ids, date_from, date_to, context=context)
        res['value'].update({
                    'input_line_ids': input_line_ids,
            })
        return res

    def onchange_contract_id(self, cr, uid, ids, date_from, date_to, employee_id=False, contract_id=False, context=None):
        if context is None:
            context = {}
        res = {'value':{
                 'line_ids': [],
                 'name': '',
                 }
              }
        context.update({'contract': True})
        if not contract_id:
            res['value'].update({'struct_id': False})
        return self.onchange_employee_id(cr, uid, ids, date_from=date_from, date_to=date_to, employee_id=employee_id, contract_id=contract_id, context=context)

hr_payslip()

class hr_payslip_input(osv.osv):
    '''
    Payslip Input
    '''

    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'payslip_id': fields.many2one('hr.payslip', 'Pay Slip', required=True),
        'sequence': fields.integer('Sequence', required=True,),
        'code': fields.char('Code', size=52, required=True, help="The code that can be used in the salary rules"),
        'number_of_days': fields.float('Number of Days'),
        'number_of_hours': fields.float('Number of Hours'),
        'contract_id': fields.many2one('hr.contract', 'Contract', required=True, help="The contract for which applied this input"),
    }
    _order = 'payslip_id,sequence'
    _defaults = {
        'sequence': 10,
    }
hr_payslip_input()

class hr_salary_rule(osv.osv):

    _name = 'hr.salary.rule'
    _columns = {
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True),
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence'),
        'category_id':fields.many2one('hr.salary.head', 'Salary Head', required=True),
        'active':fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the salary rule without removing it."),
        'appears_on_payslip': fields.boolean('Appears on Payslip', help="Used for the display of rule on payslip"),
        'parent_rule_id':fields.many2one('hr.salary.rule', 'Parent Salary Rule', select=True),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'condition_select': fields.selection([('none', 'Always True'),('range', 'Range'), ('python', 'Python Expression')], "Condition Based on", required=True),
        'condition_range':fields.char('Range Based on',size=1024, readonly=False, help='This will use to computer the % fields values, in general its on basic, but You can use all heads code field in small letter as a variable name i.e. hra, ma, lta, etc...., also you can use, static varible basic'),#old name = conputional expression
        'condition_python':fields.text('Python Condition', required=True, readonly=False, help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.'),#old name = conditions
        'condition_range_min': fields.float('Minimum Range', required=False, help="The minimum amount, applied for this rule."),
        'condition_range_max': fields.float('Maximum Range', required=False, help="The maximum amount, applied for this rule."),
        'amount_select':fields.selection([
            ('percentage','Percentage (%)'),
            ('fix','Fixed Amount'),
            ('code','Python Code'),
        ],'Amount Type', select=True, required=True, help="The computation method for the rule amount."),
        'amount_fix': fields.float('Fixed Amount', digits_compute=dp.get_precision('Account'),),
        'amount_percentage': fields.float('Percentage (%)', digits_compute=dp.get_precision('Account'), help='For example, enter 50.0 to apply a percentage of 50%'),
        'amount_python_compute':fields.text('Python Code'),
        'amount_percentage_base':fields.char('Percentage based on',size=1024, required=False, readonly=False, help='result will be affected to a variable'), #old name = expressiont
        'child_ids':fields.one2many('hr.salary.rule', 'parent_rule_id', 'Child Salary Rule'),
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
        'note':fields.text('Description'),
     }
    _defaults = {
        'amount_python_compute': '''
# Available variables:
#----------------------
# payslip: hr.payslip object
# employee: hr.employee object
# contract: hr.contract object
# rules: dictionary containing the previsouly computed rules. Keys are the rule codes.
# heads: dictionary containing the computed heads (sum of amount of all rules belonging to that head). Keys are the head codes.

# Note: returned value have to be set in the variable 'result'

result = contract.wage * 0.10''',
        'condition_python':
'''
# Available variables:
#----------------------
# payslip: hr.payslip object
# employee: hr.employee object
# contract: hr.contract object
# rules: dictionary containing the previsouly computed rules. Keys are the rule codes.
# heads: dictionary containing the computed heads (sum of amount of all rules belonging to that head). Keys are the head codes.

# Note: returned value have to be set in the variable 'result'

result = rules['NET'] > heads['NET'] * 0.10''',
        'condition_range': 'contract.wage',
        'sequence': 5,
        'appears_on_payslip': True,
        'active': True,
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
        'condition_select': 'none',
        'amount_select': 'fix',
        'amount_fix': 0.0,
        'amount_percentage': 0.0,
     }

    #TODO should add some checks on the type of result (should be float)
    def compute_rule(self, cr, uid, rule_id, localdict, context=None):
        """
        @param rule_id: id of rule to compute
        @param localdict: dictionary containing the environement in which to compute the rule
        @return: returns the result of computation as float
        """
        rule = self.browse(cr, uid, rule_id, context=context)
        if rule.amount_select == 'fix':
            return rule.amount_fix
        elif rule.amount_select == 'percentage':
            return rule.amount_percentage * eval(rule.amount_percentage_base, localdict) / 100
        else:
            eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
            return localdict['result']

    def satisfy_condition(self, cr, uid, rule_id, localdict, context=None):
        """
        @param rule_id: id of hr.salary.rule to be tested
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        rule = self.browse(cr, uid, rule_id, context=context)

        if rule.condition_select == 'none':
            return True
        elif rule.condition_select == 'range':
            result = eval(rule.condition_range, localdict)
            return rule.condition_range_min <=  result and result <= rule.condition_range_max or False
        else: #python code
            eval(rule.condition_python, localdict, mode='exec', nocopy=True)
            return 'result' in localdict and localdict['result'] or False
hr_salary_rule()

class hr_payslip_line(osv.osv):
    '''
    Payslip Line
    '''

    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'sequence'

    _columns = {
        'slip_id':fields.many2one('hr.payslip', 'Pay Slip', required=True),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'total': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'company_contrib': fields.float('Company Contribution', readonly=True, digits_compute=dp.get_precision('Account')),
    }

hr_payslip_line()

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

    def _calculate_total_wage(self, cr, uid, ids, name, args, context):
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
        'slip_ids':fields.one2many('hr.payslip', 'employee_id', 'Payslips', required=False, readonly=True),
        'total_wage': fields.function(_calculate_total_wage, method=True, type='float', string='Total Basic Salary', digits_compute=dp.get_precision('Account'), help="Sum of all current contract's wage of employee."),
    }

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
