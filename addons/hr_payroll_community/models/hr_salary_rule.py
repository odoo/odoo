# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
# from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):
    """Create new model for Salary Rule"""
    _name = 'hr.salary.rule'
    _order = 'sequence, id'
    _description = 'Salary Rule'

    name = fields.Char(required=True, translate=True, string="Salary Rule Name",
                       help="Enter Salary Rule Name")
    code = fields.Char(required=True, string="Salary Rule Code",
                       help="The code of salary rules can be used as reference"
                            "in computation of other rules. "
                            "In that case, it is case sensitive.")
    sequence = fields.Integer(required=True, index=True, default=5,
                              help='Use to arrange calculation sequence',
                              string="Sequence")
    quantity = fields.Char(default='1.0', string='Quantity',
                           help="It is used in computation for percentage"
                                "and fixed amount. For e.g. A rule for Meal"
                                "Voucher having fixed amount of "
                                u"1€ per worked day can have its quantity"
                                "defined in expression "
                                "like worked_days.WORK100.number_of_days.")
    category_id = fields.Many2one('hr.salary.rule.category',
                                  string='Category',
                                  help="Choose Salary Rule Category",
                                  required=True)
    active = fields.Boolean(default=True, string='Active',
                            help="If the active field is set to false, "
                                 "it will allow you to hide the salary"
                                 "rule without removing it.")
    appears_on_payslip = fields.Boolean(string='Appears on Payslip',
                                        default=True,
                                        help="Used to display the salary"
                                             "rule on payslip.")
    parent_rule_id = fields.Many2one('hr.salary.rule',
                                     string='Parent Salary Rule', index=True,
                                     help="Choose Hr Salary Rule")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company.id
    )
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression')
    ], string="Condition Based on", default='none', required=True,
        help="Choose Condition for Salary Rule")
    condition_range = fields.Char(string='Range Based on',
                                  default='contract.wage',
                                  help='This will be used to compute the % '
                                       'fields values; in general it is on '
                                       'basic, but you can also use categories '
                                       'code fields in lowercase as a variable'
                                       ' names (hra, ma, lta, etc.) and the '
                                       'variable basic.')
    condition_python = fields.Text(string='Python Condition', required=True,
                                   default='''
    # Available variables:
    #----------------------
    # payslip: object containing the payslips
    # employee: hr.employee object
    # contract: hr.version object
    # rules: object containing the rules code (previously computed)
    # categories: object containing the computed salary rule categories 
    # (sum of amount of all rules belonging to that category).
    # worked_days: object containing the computed worked days
    # inputs: object containing the computed inputs

    # Note: returned value have to be set in the variable 'result'

    result = rules.NET > categories.NET * 0.10''',
                                   help='Applied this rule for calculation'
                                        ' if condition is true. You can specify'
                                        ' condition like basic > 1000.')
    condition_range_min = fields.Float(string='Minimum Range',
                                       help="The minimum amount, applied for"
                                            " this rule.")
    condition_range_max = fields.Float(string='Maximum Range',
                                       help="The maximum amount, applied for"
                                            " this rule.")
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True, default='fix',
        help="The computation method for the rule amount.")

    amount_fix = fields.Float(string='Fixed Amount',
                              digits='Payroll',
                              help="Set a Fixed Amount")

    amount_percentage = fields.Float(string='Percentage (%)',
                                     digits='Payroll Rate',
                                     help='For example, enter 50.0 to apply '
                                          'a percentage of 50%')
    amount_percentage = fields.Float(string='Percentage (%)',
                                     digits='Payroll Rate',
                                     help='For example, enter 50.0 to apply '
                                          'a percentage of 50%')

    amount_python_compute = fields.Text(string='Python Code',
                                        default='''
            # Available variables:
            #----------------------
            # payslip: object containing the payslips
            # employee: hr.employee object
            # contract: hr.version object
            # rules: object containing the rules code (previously computed)
            # categories: object containing the computed salary rule categories 
            # (sum of amount of all rules belonging to that category).
            # worked_days: object containing the computed worked days.
            # inputs: object containing the computed inputs.

            # Note: returned value have to be set in the variable 'result'

            result = contract.wage * 0.10''')
    amount_percentage_base = fields.Char(string='Percentage based on',
                                         help='result will be affected to a '
                                              'variable')
    child_ids = fields.One2many('hr.salary.rule',
                                'parent_rule_id',
                                help='Child rules of the Salary rule',
                                string='Child Salary Rule', copy=True)
    register_id = fields.Many2one('hr.contribution.register',
                                  string='Contribution Register',
                                  help="Eventual third party involved in the"
                                       " salary payment of the employees.")
    input_ids = fields.One2many('hr.rule.input',
                                'input_id', string='Inputs',
                                copy=True, help="Choose Hr Rule Input")
    note = fields.Text(string='Description', help="Description for Salary Rule")

    @api.constrains('parent_rule_id')
    def _check_parent_rule_id(self):
        """Function to adding constrains for parent_rule_id field"""
        if self._has_cycle('parent_rule_id'):
            raise ValidationError(
                _('Error! You cannot create recursive hierarchy '
                  'of Salary Rules.'))

    def _recursive_search_of_rules(self):
        """
        @return: returns a list of tuple (id, sequence) which are all the
        children of the passed rule_ids
        """
        children_rules = []
        for rule in self.filtered(lambda rule: rule.child_ids):
            children_rules += rule.child_ids._recursive_search_of_rules()
        return [(rule.id, rule.sequence) for rule in self] + children_rules

    # TODO should add some checks on the type of result (should be float)
    def _compute_rule(self, localdict):
        """
        :param localdict: dictionary containing the environement in which to
            compute the rule
        :return: returns a tuple build as the base/amount computed,
            the quantity and the rate
        :rtype: (float, float, float)
        """
        for rec in self:
            rec.ensure_one()
            if rec.amount_select == 'fix':
                try:
                    return rec.amount_fix, float(
                        safe_eval(rec.quantity, localdict)), 100.0
                except:
                    raise UserError(
                        _('Wrong quantity defined for salary rule %s (%s).') % (
                            rec.name, rec.code))
            elif rec.amount_select == 'percentage':
                try:
                    return (
                        float(safe_eval(rec.amount_percentage_base, localdict)),
                        float(safe_eval(rec.quantity, localdict)),
                        rec.amount_percentage)
                except:
                    raise UserError(
                        _('Wrong percentage base or quantity defined '
                          'for salary rule %s (%s).') % (
                            rec.name, rec.code))
            else:
                try:

                    safe_eval(rec.amount_python_compute, localdict, mode='exec')
                    return (float(localdict['result']),
                            'result_qty' in localdict and
                            localdict['result_qty'] or 1.0, 'result_rate'
                            in localdict and localdict['result_rate'] or 100.0)
                except:
                    raise UserError(
                        _('Wrong python code defined for salary '
                          'rule %s (%s).') % (
                            rec.name, rec.code))

    def _satisfy_condition(self, localdict):
        """
        @param localdict: id of hr_contract to be tested
        @return: returns True if the given rule match the condition for the
        given contract. Return False otherwise.
        """
        self.ensure_one()
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return (
                            self.condition_range_min <= result <= self.condition_range_max or False)
            except:
                raise UserError(
                    _('Wrong range condition defined for '
                      'salary rule %s (%s).') % (
                        self.name, self.code))
        else:  # python code
            try:
                safe_eval(self.condition_python, localdict, mode='exec',
                          nocopy=True)
                return 'result' in localdict and localdict['result'] or False
            except:
                raise UserError(
                    _('Wrong python condition defined for '
                      'salary rule %s (%s).') % (
                        self.name, self.code))
