# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError


class HrSalaryRule(models.Model):

    _name = 'hr.salary.rule'

    name = fields.Char(required=True)
    code = fields.Char(size=64, required=True, help="The code of salary rules can be used as reference in computation of other rules. In that case, it is case sensitive.")
    sequence = fields.Integer(required=True, help='Use to arrange calculation sequence', default=5, index=True)
    quantity = fields.Char(default=1.0, help="It is used in computation for percentage and fixed amount.For e.g. A rule for Meal Voucher having fixed amount of 1€ per worked day can have its quantity defined in expression like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('hr.salary.rule.category', 'Category', required=True)
    active = fields.Boolean(default=True, help="If the active field is set to false, it will allow you to hide the salary rule without removing it.")
    appears_on_payslip = fields.Boolean(default=True, help="Used to display the salary rule on payslip.")
    parent_rule_id = fields.Many2one('hr.salary.rule', 'Parent Salary Rule', index=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    condition_select = fields.Selection([('none', 'Always True'), ('range', 'Range'), ('python', 'Python Expression')], "Condition Based on", required=True, default='none')
    condition_range = fields.Char('Range Based on', default='contract.wage', help='This will be used to compute the % fields values; in general it is on basic, but you can also use categories code fields in lowercase as a variable names (hra, ma, lta, etc.) and the variable basic.')
    condition_python = fields.Text(default="# Available variables:" +
                                           "#----------------------" +
                                           "# payslip: object containing the payslips" +
                                           "# employee: hr.employee object" +
                                           "# contract: hr.contract object" +
                                           "# rules: object containing the rules code (previously computed)" +
                                           "# categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category)." +
                                           "# worked_days: object containing the computed worked days" +
                                           "# inputs: object containing the computed inputs" +
                                           "# Note: returned value have to be set in the variable 'result'" +
                                           "result = rules.NET > categories.NET * 0.10", string='Python Condition', required=True, help='Applied this rule for calculation if condition is true. You can specify condition like basic > 1000.')
    condition_range_min = fields.Float('Minimum Range', help="The minimum amount, applied for this rule.")
    condition_range_max = fields.Float('Maximum Range', help="The maximum amount, applied for this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ],'Amount Type', default='fix', index=True, required=True, help="The computation method for the rule amount.")
    amount_fix = fields.Float('Fixed Amount', digits=dp.get_precision('Payroll'), default=0.0)
    amount_percentage = fields.Float('Percentage (%)', digits=dp.get_precision('Payroll Rate'), default=0.0, help='For example, enter 50.0 to apply a percentage of 50%')
    amount_python_compute = fields.Text('Python Code')
    amount_percentage_base = fields.Char('Percentage based on', help='result will be affected to a variable')
    child_ids = fields.One2many('hr.salary.rule', 'parent_rule_id', 'Child Salary Rule', copy=True)
    register_id = fields.Many2one('hr.contribution.register', 'Contribution Register', help="Eventual third party involved in the salary payment of the employees.")
    input_ids = fields.One2many('hr.rule.input', 'input_id', 'Inputs', copy=True)
    note = fields.Text('Description')

    def _recursive_search_of_rules(self):
        """
        :return: returns a list of tuple (id, sequence) which are all the children of the passed rule_ids
        """
        children_rules = []
        for rule in self.filtered(lambda x: x.child_ids):
            children_rules += self._recursive_search_of_rules()
        return [(r, r.sequence) for r in self] + children_rules

    # TODO should add some checks on the type of result (should be float)
    @api.multi
    def compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to compute the rule
        :return: returns a tuple build as the base/amount computed, the quantity and the rate
        :rtype: (float, float, float)
        """
        self.ensure_one()
        if self.amount_select == 'fix':
            try:
                return self.amount_fix, float(eval(self.quantity, localdict)), 100.0
            except:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
        elif self.amount_select == 'percentage':
            try:
                return (float(eval(self.amount_percentage_base, localdict)),
                        float(eval(self.quantity, localdict)),
                        self.amount_percentage)
            except:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code))
        else:
            try:
                eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code))

    def satisfy_condition(self, localdict):
        """
        :return: returns True if the given rule match the condition for the given contract. Return False otherwise.
        """
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = eval(self.condition_range, localdict)
                return self.condition_range_min <= result and result <= self.condition_range_max or False
            except:
                raise UserError(_('Wrong range condition defined for salary rule %s (%s).') % (self.name, self.code))
        else: # python code
            try:
                eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError(_('Wrong python condition defined for salary rule %s (%s).') % (self.name, self.code))


class HrSalaryRuleCategory(models.Model):
    """
    HR Salary Rule Category
    """

    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'

    name = fields.Char(required=True)
    code = fields.Char(size=64, required=True)
    parent_id = fields.Many2one('hr.salary.rule.category', 'Parent', help="Linking a salary category to its parent is used only for the reporting purpose.")
    children_ids = fields.One2many('hr.salary.rule.category', 'parent_id', 'Children')
    note = fields.Text('Description')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id)


class HrRuleInput(models.Model):
    '''
    Salary Rule Input
    '''

    _name = 'hr.rule.input'
    _description = 'Salary Rule Input'

    name = fields.Char('Description', required=True)
    code = fields.Char(size=52, required=True, help="The code that can be used in the salary rules")
    input_id = fields.Many2one('hr.salary.rule', 'Salary Rule Input', required=True)
