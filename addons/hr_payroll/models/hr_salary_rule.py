#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError


class hr_salary_rule(osv.osv):

    _name = 'hr.salary.rule'
    _columns = {
        'name':fields.char('Name', required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, help="The code of salary rules can be used as reference in computation of other rules. In that case, it is case sensitive."),
        'sequence': fields.integer('Sequence', required=True, help='Use to arrange calculation sequence', select=True),
        'quantity': fields.char('Quantity', help=u"It is used in computation for percentage and fixed amount.For e.g. A rule for Meal Voucher having fixed amount of 1€ per worked day can have its quantity defined in expression like worked_days.WORK100.number_of_days."),
        'category_id':fields.many2one('hr.salary.rule.category', 'Category', required=True),
        'active':fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the salary rule without removing it."),
        'appears_on_payslip': fields.boolean('Appears on Payslip', help="Used to display the salary rule on payslip."),
        'parent_rule_id':fields.many2one('hr.salary.rule', 'Parent Salary Rule', select=True),
        'company_id':fields.many2one('res.company', 'Company', required=False),
        'condition_select': fields.selection([('none', 'Always True'),('range', 'Range'), ('python', 'Python Expression')], "Condition Based on", required=True),
        'condition_range':fields.char('Range Based on', readonly=False, help='This will be used to compute the % fields values; in general it is on basic, but you can also use categories code fields in lowercase as a variable names (hra, ma, lta, etc.) and the variable basic.'),
        'condition_python':fields.text('Python Condition', required=True, readonly=False, help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.'),
        'condition_range_min': fields.float('Minimum Range', required=False, help="The minimum amount, applied for this rule."),
        'condition_range_max': fields.float('Maximum Range', required=False, help="The maximum amount, applied for this rule."),
        'amount_select':fields.selection([
            ('percentage','Percentage (%)'),
            ('fix','Fixed Amount'),
            ('code','Python Code'),
        ],'Amount Type', select=True, required=True, help="The computation method for the rule amount."),
        'amount_fix': fields.float('Fixed Amount', digits_compute=dp.get_precision('Payroll'),),
        'amount_percentage': fields.float('Percentage (%)', digits_compute=dp.get_precision('Payroll Rate'), help='For example, enter 50.0 to apply a percentage of 50%'),
        'amount_python_compute':fields.text('Python Code'),
        'amount_percentage_base': fields.char('Percentage based on', required=False, readonly=False, help='result will be affected to a variable'),
        'child_ids':fields.one2many('hr.salary.rule', 'parent_rule_id', 'Child Salary Rule', copy=True),
        'register_id':fields.many2one('hr.contribution.register', 'Contribution Register', help="Eventual third party involved in the salary payment of the employees."),
        'input_ids': fields.one2many('hr.rule.input', 'input_id', 'Inputs', copy=True),
        'note':fields.text('Description'),
     }
    _defaults = {
        'amount_python_compute': '''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days.
# inputs: object containing the computed inputs.

# Note: returned value have to be set in the variable 'result'

result = contract.wage * 0.10''',
        'condition_python':
'''
# Available variables:
#----------------------
# payslip: object containing the payslips
# employee: hr.employee object
# contract: hr.contract object
# rules: object containing the rules code (previously computed)
# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
# worked_days: object containing the computed worked days
# inputs: object containing the computed inputs

# Note: returned value have to be set in the variable 'result'

result = rules.NET > categories.NET * 0.10''',
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
        'quantity': '1.0',
     }

    @api.cr_uid_ids_context
    def _recursive_search_of_rules(self, cr, uid, rule_ids, context=None):
        """
        @param rule_ids: list of browse record
        @return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids
        """
        children_rules = []
        for rule in rule_ids:
            if rule.child_ids:
                children_rules += self._recursive_search_of_rules(cr, uid, rule.child_ids, context=context)
        return [(r.id, r.sequence) for r in rule_ids] + children_rules

    #TODO should add some checks on the type of result (should be float)
    def compute_rule(self, cr, uid, rule_id, localdict, context=None):
        """
        :param rule_id: id of rule to compute
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        rule = self.browse(cr, uid, rule_id, context=context)
        if rule.amount_select == 'fix':
            try:
                return rule.amount_fix, float(eval(rule.quantity, localdict)), 100.0
            except:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (rule.name, rule.code))
        elif rule.amount_select == 'percentage':
            try:
                return (float(eval(rule.amount_percentage_base, localdict)),
                        float(eval(rule.quantity, localdict)),
                        rule.amount_percentage)
            except:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (rule.name, rule.code))
        else:
            try:
                eval(rule.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (rule.name, rule.code))

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
            try:
                result = eval(rule.condition_range, localdict)
                return rule.condition_range_min <=  result and result <= rule.condition_range_max or False
            except:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s).') % (rule.name, rule.code))
        else: #python code
            try:
                eval(rule.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError(_('Wrong python condition defined for salary rule %s (%s).') % (rule.name, rule.code))


class hr_salary_rule_category(osv.osv):
    """
    HR Salary Rule Category
    """

    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'
    _columns = {
        'name':fields.char('Name', required=True, readonly=False),
        'code':fields.char('Code', size=64, required=True, readonly=False),
        'parent_id':fields.many2one('hr.salary.rule.category', 'Parent', help="Linking a salary category to its parent is used only for the reporting purpose."),
        'children_ids': fields.one2many('hr.salary.rule.category', 'parent_id', 'Children'),
        'note': fields.text('Description'),
        'company_id':fields.many2one('res.company', 'Company', required=False),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, context: \
                self.pool.get('res.users').browse(cr, uid, uid,
                    context=context).company_id.id,
    }

class hr_rule_input(osv.osv):
    '''
    Salary Rule Input
    '''

    _name = 'hr.rule.input'
    _description = 'Salary Rule Input'
    _columns = {
        'name': fields.char('Description', required=True),
        'code': fields.char('Code', size=52, required=True, help="The code that can be used in the salary rules"),
        'input_id': fields.many2one('hr.salary.rule', 'Salary Rule Input', required=True)
    }

