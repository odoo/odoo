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

#    def _total_contrib(self, cr, uid, ids, field_names, arg, context=None):
#        line_pool = self.pool.get('hr.contibution.register.line')
#
#        res = {}
#        for cur in self.browse(cr, uid, ids, context=context):
#            current = line_pool.search(cr, uid, [('register_id','=',cur.id)], context=context)
#            e_month = 0.0
#            c_month = 0.0
#            for i in line_pool.browse(cr, uid, current, context=context):
#                e_month += i.emp_deduction
#                c_month += i.comp_deduction
#            res[cur.id]={
#                'monthly_total_by_emp':e_month,
#                'monthly_total_by_comp':c_month,
#            }
#        return res

    _columns = {
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'name':fields.char('Name', size=256, required=True, readonly=False),
        'register_line_ids':fields.one2many('hr.contibution.register.line', 'register_id', 'Register Line', readonly=True),
#        'monthly_total_by_emp': fields.function(_total_contrib, method=True, multi='dc', string='Total By Employee', digits=(16, 4)),
#        'monthly_total_by_comp': fields.function(_total_contrib, method=True, multi='dc', string='Total By Company', digits=(16, 4)),
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


    def _get_salary_rules(self, cr, uid, ids, field_names, arg=None, context=None):
        structure_obj = self.pool.get('hr.payroll.structure')
        contract_obj = self.pool.get('hr.contract')
        res = {}
        rules = []
        contracts = []
        structures = []
        rule_ids = []
        sorted_salary_heads = []
        for record in self.browse(cr, uid, ids, context=context):
            if record.contract_id:
                contracts.append(record.contract_id.id)
            else:
                contracts = self.get_contract(cr, uid, record.employee_id, record.date, context=context)
            for contract in contracts:
                structures = contract_obj.get_all_structures(cr, uid, [contract], context)
            res[record.id] = {}
            for struct in structures:
                rule_ids = structure_obj.get_all_rules(cr, uid, [struct], context=None)
                for rl in rule_ids:
                    if rl[0] not in rules:
                        rules.append(rl[0])
            cr.execute('''SELECT sr.id FROM hr_salary_rule as sr, hr_salary_head as sh
               WHERE sr.category_id = sh.id AND sr.id in %s ORDER BY sh.sequence''',(tuple(rules),))
            for x in cr.fetchall():
                sorted_salary_heads.append(x[0])
            for fn in field_names:
               if fn == 'details_by_salary_head':
                   res[record.id] = {fn: sorted_salary_heads}
        return res


    #TODO clean
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
        'name': fields.char('Description', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
        'number': fields.char('Number', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
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
        'details_by_salary_head': fields.function(_get_salary_rules, method=True, type='one2many', relation='hr.salary.rule', string='Details by Salary Head', multi='details_by_salary_head'),
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
        slip_line_pool = self.pool.get('hr.payslip.line')
        for payslip in self.browse(cr, uid, ids, context=context):
            if payslip.contract_id:
                #set the list of contract for which the rules have to be applied
                contract_ids = [payslip.contract_id.id]
            else:
                #if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, payslip.employee_id, payslip.date_from, payslip.date_to, context=context)
            lines = self.pool.get('hr.payslip').get_payslip_lines(cr, uid, contract_ids, payslip.id, context=context)
            for line in lines:
                line.update({'slip_id': payslip.id})
                slip_line_pool.create(cr, uid, line, {})
#            self.write(cr, uid, [payslip.id], {'line_ids': lines}, context=context)
        return True
#        func_pool = self.pool.get('hr.payroll.structure')
#        slip_line_pool = self.pool.get('hr.payslip.line')
#        holiday_pool = self.pool.get('hr.holidays')
#        sequence_obj = self.pool.get('ir.sequence')
#        salary_rule_pool = self.pool.get('hr.salary.rule')
#        contract_obj = self.pool.get('hr.contract')
#        resource_attendance_pool = self.pool.get('resource.calendar.attendance')
#        if context is None:
#            context = {}
#
#        for slip in self.browse(cr, uid, ids, context=context):
#            old_slip_ids = slip_line_pool.search(cr, uid, [('slip_id', '=', slip.id)], context=context)
#            if old_slip_ids:
#                slip_line_pool.unlink(cr, uid, old_slip_ids, context=context)
#            update = {}
#            ttyme = datetime.fromtimestamp(time.mktime(time.strptime(slip.date, "%Y-%m-%d")))
#            contract_id = slip.contract_id.id
#            if not contract_id:
#                update.update({'struct_id': False})
#                contracts = self.get_contract(cr, uid, slip.employee_id, slip.date, context=context)
#            else:
#                contracts = contract_obj.browse(cr, uid, [contract_id], context=context)
#            if not contracts:
#                update.update({
#                    'basic_amount': 0.0,
#                    'basic_before_leaves': 0.0,
#                    'name': 'Salary Slip of %s for %s' % (slip.employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#                    'state': 'draft',
#                    'contract_id': False,
#                    'struct_id': False,
#                    'company_id': slip.employee_id.company_id.id
#                })
#                self.write(cr, uid, [slip.id], update, context=context)
#                continue
#            net_allow = 0.0
#            net_deduct = 0.0
#            all_basic = 0.0
#            for contract in contracts:
#                sal_structure = []
#                rules = []
#                all_basic += contract.wage
#                if contract.struct_id.id:
#                    sal_structure = self._get_parent_structure(cr, uid, [contract.struct_id.id], context=context)
#                for struct in sal_structure:
#                    lines = func_pool.browse(cr, uid, struct, context=context).rule_ids
#                    for rl in lines:
#                        if rl.child_ids:
#                            for r in rl.child_ids:
#                                lines.append(r)
#                        rules.append(rl)
#                ad = []
#                total = 0.0
#                obj = {'basic': contract.wage}
#                for line in rules:
#                    cd = line.code
#                    base = line.computational_expression
#                    amt = eval(base, obj)
#                    if line.amount_type == 'per':
#                        al = line.amount * amt
#                        obj[cd] = al
#                    elif line.amount_type == 'code':
#                        localdict = {'basic': amt, 'employee': slip.employee_id, 'contract': contract}
#                        exec line.python_compute in localdict
#                        val = localdict['result']
#                        obj[cd] = val
#                    else:
#                        obj[cd] = line.amount or 0.0
#
#                for line in rules:
#                    #Removing below condition because it stop to append child rule in payslip line and does not allow child rule to consider in calculation
##                    if line.category_id.code in ad:
##                        continue
#
#                    ad.append(line.category_id.code)
#                    cd = line.category_id.code.lower()
#                    calculate = False
#                    try:
#                        exp = line.conditions
#                        exec line.conditions in obj
#                        calculate = eval(exp, obj)
#                    except Exception, e:
#                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#
#                    if not calculate:
#                        continue
#
#                    value = 0.0
#                    base = line.computational_expression
#                    try:
#                        amt = eval(base, obj)
#                    except Exception, e:
#                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#                    if line.amount_type == 'per':
#                        try:
##                            if line.child_depend == False:
#                            if line.parent_rule_id:
#                                for rul in [line.parent_rule_id]:
#                                    val = rul.amount * amt
#                                    amt = val
#                            value = line.amount * amt
#                            if line.condition_range_min or line.condition_range_max:
#                                if ((value < line.condition_range_min) or (value > line.condition_range_max)):
#                                    value = 0.0
#                                else:
#                                    value = value
#                            else:
#                                value = value
#                        except Exception, e:
#                            raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#
#                    elif line.amount_type == 'fix':
##                        if line.child_depend == False:
#                        if line.parent_rule_id:
#                            for rul in [line.parent_rule_id]:
#                                value = value
#                        if line.condition_range_min or line.condition_range_max:
#                            if ((line.amount < line.condition_range_min) or (line.amount > line.condition_range_max)):
#                                value = value
#                            else:
#                                value = line.amount
#                        else:
#                            value = line.amount
#
#                    elif line.amount_type == 'code':
#                        localdict = {'basic': amt, 'employee': slip.employee_id, 'contract': contract}
#                        exec line.python_compute in localdict
#                        val = localdict['result']
##                        if line.child_depend == False:
#                        if line.parent_rule_id:
#                            for rul in [line.parent_rule_id]:
#                                value = val
#                        if line.condition_select == 'range':
#                            if line.condition_range_min or line.condition_range_max:
#                                if ((line.amount < line.condition_range_min) or (line.amount > line.condition_range_max)):
#                                    value = value
#                                else:
#                                    value = val
#                        else:
#                            value = val
#                    if value < 0:
#                        net_deduct += value
#                    else:
#                        net_allow += value
#                    total += value
#                    vals = {
#                        'slip_id': slip.id,
#                        'category_id': line.category_id.id,
#                        'name': line.name,
#                        'sequence': line.sequence,
#                        #'type': line.type.id,
#                        'code': line.code,
#                        'amount_type': line.amount_type,
#                        'amount': line.amount,
#                        'total': value,
#                        'employee_id': slip.employee_id.id,
#                        'base': line.computational_expression
#                    }
#                    slip_ids = slip_line_pool.search(cr, uid, [('code', '=', line.code), ('slip_id', '=', slip.id)])
#                    if not slip_ids:
#                        if line.appears_on_payslip:
#                            if line.condition_range_min or line.condition_range_max:
#                                if not ((value < line.condition_range_min) or (value > line.condition_range_max)):
#                                    slip_line_pool.create(cr, uid, vals, {})
#                            else:
#                                slip_line_pool.create(cr, uid, vals, {})
#
#                basic = contract.wage
#                basic_before_leaves = slip.basic_amount
#                working_day = 0
#                off_days = 0
#                dates = prev_bounds(slip.date)
#                calendar_id = slip.employee_id.contract_id.working_hours.id
#                if not calendar_id:
#                    raise osv.except_osv(_('Error !'), _("Please define working schedule on %s's contract") % (slip.employee_id.name))
#                week_days = {"0": "mon", "1": "tue", "2": "wed","3": "thu", "4": "fri", "5": "sat", "6": "sun"}
#                wk_days = {}
#                week_ids = resource_attendance_pool.search(cr, uid, [('calendar_id', '=', calendar_id)], context=context)
#                weeks = resource_attendance_pool.read(cr, uid, week_ids, ['dayofweek'], context=context)
#                for week in weeks:
#                    if week_days.has_key(week['dayofweek']):
#                        wk_days[week['dayofweek']] = week_days[week['dayofweek']]
#                days_arr = [0, 1, 2, 3, 4, 5, 6]
#                for dy in range(len(wk_days), 7):
#                    off_days += get_days(1, dates[1].day, dates[1].month, dates[1].year, days_arr[dy])
#                total_off = off_days
#                working_day = dates[1].day - total_off
##                perday = working_day and basic / working_day or 0.0
#                total = 0.0
#                leave = 0.0
#                leave_ids = self._get_leaves(cr, uid, slip.date, slip.employee_id, contract, context)
#                total_leave = 0.0
#                paid_leave = 0.0
#                h_ids = holiday_pool.browse(cr, uid, leave_ids, context=context)
#                for hday in holiday_pool.browse(cr, uid, leave_ids, context=context):
#    #                if not hday.holiday_status_id.head_id:
#    #                    raise osv.except_osv(_('Error !'), _('Please check configuration of %s, payroll head is missing') % (hday.holiday_status_id.name))
#                    slip_lines = salary_rule_pool.search(cr, uid, [('code', '=', hday.holiday_status_id.code)], context=context)
#                    if not slip_lines:
#                        raise osv.except_osv(_('Error !'), _('Salary rule is not defined for %s. Please check the configuration') % (hday.holiday_status_id.name))
#                    salary_rule = salary_rule_pool.browse(cr, uid, slip_lines, context=context)[0]
#                    base = salary_rule.computational_expression
#                    obj = {'basic': hday.contract_id.wage}
#                    res = {
#                        'slip_id': slip.id,
#                        'name': salary_rule.name + '-%s' % (hday.number_of_days),
#                        'code': salary_rule.code,
#                        'amount_type': salary_rule.amount_type,
#                        'category_id': salary_rule.category_id.id,
#                        'sequence': salary_rule.sequence,
#                        'employee_id': slip.employee_id.id,
#                        'base': base
#                    }
#                    days = hday.number_of_days
#                    if hday.number_of_days < 0:
#                        days = hday.number_of_days * -1
#                    total_leave += days
#                    try:
#                        amt = eval(base, obj)
#                    except Exception, e:
#                        raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#                    if salary_rule.amount_type == 'per':
#                        try:
#    #                        if salary_rule.child_depend == False:
#                            if salary_rule.parent_rule_id:
#                                for rul in [salary_rule.parent_rule_id]:
#                                    val = rul.amount * amt
#                                    amt = val
#                            value = salary_rule.amount * amt * days
#                            if salary_rule.condition_select == 'range':
#                                if salary_rule.condition_range_min or salary_rule.condition_range_max:
#                                    if ((value < salary_rule.condition_range_min) or (value > salary_rule.condition_range_max)):
#                                        value = 0.0
#                                    else:
#                                        value = value
#                            else:
#                                value = value
#                        except Exception, e:
#                            raise osv.except_osv(_('Variable Error !'), _('Variable Error: %s ') % (e))
#
#                    elif salary_rule.amount_type == 'fix':
#    #                    if salary_rule.child_depend == False:
#                        if salary_rule.parent_rule_id:
#                            for rul in [salary_rule.parent_rule_id]:
#                                value = salary_rule.amount * days
#                        elif salary_rule.condition_select == 'range':
#                            if salary_rule.condition_range_min or salary_rule.condition_range_max:
#                                if ((salary_rule.amount < salary_rule.condition_range_min) or (salary_rule.amount > salary_rule.condition_range_max)):
#                                    value = 0.0
#                                else:
#                                    value = salary_rule.amount * days
#                        else:
#                            value = salary_rule.amount * days
#
#                    elif salary_rule.amount_type == 'code':
#                        localdict = {'basic': amt, 'employee': slip.employee_id, 'contract': contract}
#                        exec salary_rule.python_compute in localdict
#                        val = localdict['result'] * days
#    #                    if salary_rule.child_depend == False:
#                        if salary_rule.parent_rule_id:
#                            for rul in [salary_rule.parent_rule_id]:
#                                value = val
#                        if salary_rule.condition_select == 'range':
#                            if salary_rule.condition_range_min or salary_rule.condition_range_max:
#                                if ((salary_rule.amount < salary_rule.condition_range_min) or (salary_rule.amount > salary_rule.condition_range_max)):
#                                    value = value
#                                else:
#                                    value = val
#                        else:
#                            value = val
#                    if value < 0:
#                        net_deduct += value
#                    else:
#                        net_allow += value
#                    res['amount'] = salary_rule.amount
#                    #res['type'] = salary_rule.type.id
#                    leave += days
#                    total += value
#                    res['total'] = value
#                    if salary_rule.appears_on_payslip:
#                        if salary_rule.condition_range_min or salary_rule.condition_range_max:
#                            if not ((value < salary_rule.condition_range_min) or (value > salary_rule.condition_range_max)):
#                                slip_line_pool.create(cr, uid, res, context=context)
#                        else:
#                            slip_line_pool.create(cr, uid, res, context=context)
#
#                holiday_pool.write(cr, uid, leave_ids, {'payslip_id': slip.id}, context=context)
#                basic = basic - total
#
#            net_id = salary_rule_pool.search(cr, uid, [('code', '=', 'NET')])
#            for line in salary_rule_pool.browse(cr, uid, net_id, context=context):
#                dic = {'basic': all_basic, 'allowance': net_allow, 'deduction': net_deduct}
#                exec line.python_compute in dic
#                tot = dic['total']
#                vals = {
#                    'slip_id': slip.id,
#                    'category_id': line.category_id.id,
#                    'name': line.name,
#                    'sequence': line.sequence,
#                    #'type': line.type.id,
#                    'code': line.code,
#                    'amount_type': line.amount_type,
#                    'amount': line.amount,
#                    'total': tot,
#                    'employee_id': slip.employee_id.id,
#                    'base': line.computational_expression
#                }
#            slip_line_pool.create(cr, uid, vals, context=context)
#            number = sequence_obj.get(cr, uid, 'salary.slip')
#            update.update({
#                'number': number,
#                'name': 'Salary Slip of %s for %s' % (slip.employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),
#                'basic_amount': basic_before_leaves,
#                'basic_before_leaves': basic_before_leaves,
#                'total_pay': basic + total,
#                'leaves': total,
#                'state':'draft',
#                'holiday_days': leave,
#                'worked_days': working_day - leave,
#                'working_days': working_day,
#                'company_id': slip.employee_id.company_id.id
#            })
#        return self.write(cr, uid, [slip.id], update, context=context)

    def get_input_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
        """
        @param contract_ids: list of contract id
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            if not contract.working_hours:
                #fill only if the contract as a working schedule linked
                continue
            
            day_from = datetime.strptime(date_from,"%Y-%m-%d")
            day_to = datetime.strptime(date_to,"%Y-%m-%d")
            nb_of_days = day_to - day_from 
            for day in range(1,nb_of_days.days):
                continue
                #TODO deal with the multiple types!!!
                #TODO define the check_day_for_input function
                if check_day_for_input(day_from + timedelta(days=day),contract.working_hours.attendance_ids):
                    #TODO add the input vals to tmp (increment if existing)
                    tmp = {}
                    res.append(tmp)
        return res

    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        result = []
        localdict = {}
        #get the ids of the structures on the contracts and their parent id as well 
        structure_ids = self.pool.get('hr.contract').get_all_structures(cr, uid, contract_ids, context=context)
        #get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        #run the rules by sequence
        #import pdb;pdb.set_trace()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
         
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            for rule in self.pool.get('hr.salary.rule').browse(cr, uid, sorted_rule_ids, context=context):
                #check if the rule can be applied
                if self.pool.get('hr.salary.rule').satisfy_condition(cr, uid, rule.id, contract.id, payslip_id, context=context):
                    amount = self.pool.get('hr.salary.rule').compute_rule(cr, uid, rule.id, contract.id, payslip_id, localdict, context=context)
                    localdict[rule.code] = amount
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
        #delete old payslip lines
        old_slipline_ids = ids and slip_line_pool.search(cr, uid, [('slip_id', '=', ids[0])], context=context) or False
        if old_slipline_ids:
            slip_line_pool.unlink(cr, uid, old_slipline_ids, context=context)

        #defaults
        res = {'value':{
                      'line_ids':[], 
                      'details_by_salary_head':[], 
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
                res['value'].update({'struct_id': contract_record.struct_id.id})
            else:
                #if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
                if not contract_ids:
                    return res

        #computation of the salary input
        input_line_ids = self.get_input_lines(cr, uid, contract_ids, date_from, date_to, context=context)
        res['value'].update({
                    'input_line_ids': input_line_ids,
                    #self.get_payslip_lines_from_contracts(cr, uid, contract_ids, context=context),
                    #'details_by_salary_head': , TODO: check this out
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

#class hr_holidays(osv.osv):
#
#    _inherit = "hr.holidays"
#    _columns = {
#        'payslip_id': fields.many2one('hr.payslip', 'Payslip'),
#        'contract_id': fields.many2one('hr.contract', 'Contract', readonly=True, states={'draft':[('readonly',False)]})
#    }
#
#    def onchange_employee_id(self, cr, uid, ids, employee_id=False, date_from=False, context=None):
#        if not employee_id:
#            return {}
#        contract_obj = self.pool.get('hr.contract')
#        res = {}
#        employee_id = self.pool.get('hr.employee').browse(cr, uid, employee_id, context)
#
#        # fix me: Date_from is not comming in onchange..
#        contract_ids = self.pool.get('hr.payslip').get_contract(cr, uid, employee_id, date_from, date_to context=context)
#        res.update({
#            'contract_id': contract_ids and contract_ids[0].id or False,
#        })
#        return {'value': res}
#
#hr_holidays()

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
        'condition_select': fields.selection([('none', 'Always True'),('range', 'Range'), ('python', 'Python Expression')], "Condition Based on"),
        'condition_range':fields.char('Range Based on',size=1024, readonly=False, help='This will use to computer the % fields values, in general its on basic, but You can use all heads code field in small letter as a variable name i.e. hra, ma, lta, etc...., also you can use, static varible basic'),#old name = conputional expression
        'condition_python':fields.char('Python Condition', size=1024, required=True, readonly=False, help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.'),#old name = conditions
        'condition_range_min': fields.float('Minimum Range', required=False, help="The minimum amount, applied for this rule."),
        'condition_range_max': fields.float('Maximum Range', required=False, help="The maximum amount, applied for this rule."),
        'amount_select':fields.selection([
            ('percentage','Percentage (%)'),
            ('fix','Fixed Amount'),
            ('code','Python Code'),
        ],'Amount Type', select=True, required=True, help="The computation method for the rule amount."),
        'amount_fix': fields.float('Fixed Amount', digits_compute=dp.get_precision('Account'),),
        'amount_percentage': fields.float('Percentage', digits_compute=dp.get_precision('Account'), help='Enter a number between -1 and 1'),
        'amount_python_compute':fields.text('Python Code'),
        'amount_percentage_base':fields.char('Expression based on',size=1024, required=False, readonly=False, help='result will be affected to a variable'), #old name = expressiont
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
        'amount_python_compute': '''# basic\n# employee: hr.employee object or None\n# contract: hr.contract object or None\n\nresult = basic * 0.10''',
        'condition_python': 'result = True',
        'condition_range': 'result = contract.wage',
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

    def onchange_company(self, cr, uid, ids, company_contribution=False, context=None):
        if company_contribution:
            return {'value': {'appears_on_payslip': False}}
        return {'value': {}}

    def compute_rule(self, cr, uid, rule_id, contract_id, payslip_id, localdict, context=None):
        rule = self.browse(cr, uid, rule_id, context=context)
        contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, context=context)
        employee = contract.employee_id
        payslip = self.pool.get('hr.payslip').browse(cr, uid, payslip_id, context=context)
        localdict.update({'employee': employee, 'contract': contract, 'payslip': payslip})
        if rule.amount_select == 'fix':
            return rule.amount_fix
        elif rule.amount_select == 'percentage':
            #TODO use safe_eval
            exec rule.amount_percentage_base in localdict
            return rule.amount_percentage * localdict['result']
        else:
            #TODO use safe_eval
            exec rule.amount_python_compute in localdict
            return localdict['result']

    def satisfy_condition(self, cr, uid, rule_id, contract_id, payslip_id, context=None):
        """
        @param rule_id: id of hr.salary.rule to be tested
        @param contract_id: id of hr.contract to be tested
        @return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        rule = self.browse(cr, uid, rule_id, context=context)
        contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, context=context)
        employee = contract.employee_id
        payslip = self.pool.get('hr.payslip').browse(cr, uid, payslip_id, context=context)
        localdict = {'employee': employee, 'contract': contract, 'payslip': payslip}

        if rule.condition_select == 'none':
            return True
        elif rule.condition_select == 'range':
            #TODO use safe_eval
            exec rule.condition_range in localdict
            return rule.condition_range_min <=  localdict['result'] and localdict['result'] <= rule.condition_range_max or False
        else: #python code
            #TODO use safe_eval
            exec rule.condition_python in localdict
            return 'result' in localdict and localdict['result'] or False
        return False
hr_salary_rule()

class hr_payslip_line(osv.osv):
    '''
    Payslip Line
    '''

    _name = 'hr.payslip.line'
    _inherit = 'hr.salary.rule'
    _description = 'Payslip Line'
    _order = 'sequence'

    def onchange_category(self, cr, uid, ids, category_id=False):
        if not category_id:
            return {}
        res = {}
        category = self.pool.get('hr.salary.head').browse(cr, uid, category_id)
        res.update({
            'name': category.name,
            'code': category.code,
        })
        return {'value': res}

    _columns = {
        'slip_id':fields.many2one('hr.payslip', 'Pay Slip', required=True),
        'employee_id':fields.many2one('hr.employee', 'Employee', required=True),
        'total': fields.float('Sub Total', digits_compute=dp.get_precision('Account')),
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
        'slip_ids':fields.one2many('hr.payslip', 'employee_id', 'Payslips', required=False, readonly=True),
        'basic': fields.function(_calculate_basic, method=True, multi='dc', type='float', string='Basic Salary', digits_compute=dp.get_precision('Account'), help="Sum of all current contract's wage of employee."),
    }

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
