from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CustomPayrollRule(models.Model):
    _name = 'custom.payroll.rule'
    _description = 'Flexible Salary Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True, translate=True)
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique short code. Used as identifier and in descriptions.',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    amount_mode = fields.Selection(
        selection=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage'),
            ('python', 'Advanced Python'),
        ],
        string='Computation Mode',
        default='fixed',
        required=True,
    )
    amount_base = fields.Selection(
        selection=[
            ('basic_salary', 'Basic Salary'),
            ('contract_wage', 'Contract Wage'),
            ('gross', 'Gross Earnings'),
            ('net', 'Net Salary'),
            ('allowance', 'Allowance'),
            ('overtime', 'Overtime'),
            ('bpjs', 'BPJS'),
        ],
        string='Percentage Base',
    )
    amount_value = fields.Float(string='Amount / Percentage', default=0.0)
    condition_mode = fields.Selection(
        selection=[
            ('simple', 'Simple Condition'),
            ('python', 'Advanced Python'),
        ],
        string='Condition Mode',
        default='simple',
        required=True,
    )
    condition_type = fields.Selection(
        selection=[
            ('always', 'Always Apply'),
            ('department', 'Employee Department'),
            ('job', 'Employee Job'),
            ('active', 'Employee Active'),
            ('basic_salary', 'Basic Salary'),
            ('contract_wage', 'Contract Wage'),
            ('payroll_month', 'Payroll Month'),
            ('category', 'Salary Category'),
        ],
        string='Condition',
        default='always',
    )
    condition_operator = fields.Selection(
        selection=[
            ('=', 'Equals'),
            ('!=', 'Not Equals'),
            ('>', 'Greater Than'),
            ('>=', 'Greater Than or Equal'),
            ('<', 'Less Than'),
            ('<=', 'Less Than or Equal'),
        ],
        string='Operator',
        default='=',
    )
    condition_department_id = fields.Many2one('hr.department', string='Department')
    condition_job_id = fields.Many2one('hr.job', string='Job Position')
    condition_value_float = fields.Float(string='Value')
    condition_value_bool = fields.Boolean(string='Expected Value', default=True)
    condition_month = fields.Selection(
        selection=[
            ('1', 'January'), ('2', 'February'), ('3', 'March'),
            ('4', 'April'), ('5', 'May'), ('6', 'June'),
            ('7', 'July'), ('8', 'August'), ('9', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December'),
        ],
        string='Month',
    )
    condition_category = fields.Selection(
        selection=[
            ('BASIC', 'Basic Salary'),
            ('TUNJANGAN', 'Allowance'),
            ('LEMBUR', 'Overtime'),
            ('POTONGAN', 'Deduction'),
            ('BPJS', 'BPJS'),
            ('NET', 'Net Salary'),
        ],
        string='Salary Category',
    )
    category_id = fields.Many2one(
        'custom.payroll.rule.category',
        string='Category',
        required=True,
    )
    condition = fields.Text(
        string='Condition (Python)',
        default='True',
        help='Python expression that returns True/False. '
             'Available variables: employee, contract, payslip, categories, result. '
             'Example: payslip.payroll_batch_id.periode_bulan == "12"',
    )
    amount_python = fields.Text(
        string='Amount Computation (Python)',
        default='result = 0.0',
        help='Python code that sets the "result" variable. '
             'Available variables: employee, contract, payslip, categories, result. '
             'Examples:\n'
             '  result = categories.BASIC * 0.05\n'
             '  result = contract.contract_wage * 0.5\n'
             '  result = 500000 if employee.children > 2 else 0',
    )
    appears_on_payslip = fields.Boolean(
        string='Appears on Payslip',
        default=True,
        help='If checked, this rule will generate a line on the payslip.',
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    _code_company_uniq = models.Constraint(
        'unique(code, company_id)',
        'Code must be unique per company!',
    )

    @api.constrains(
        'condition_mode', 'condition_type', 'condition_department_id',
        'condition_job_id', 'condition_month', 'condition_category',
    )
    def _check_simple_condition(self):
        for rule in self:
            if rule.condition_mode != 'simple':
                continue
            if rule.condition_type == 'department' and not rule.condition_department_id:
                raise ValidationError('A department is required for this condition.')
            if rule.condition_type == 'job' and not rule.condition_job_id:
                raise ValidationError('A job position is required for this condition.')
            if rule.condition_type == 'payroll_month' and not rule.condition_month:
                raise ValidationError('A payroll month is required for this condition.')
            if rule.condition_type == 'category' and not rule.condition_category:
                raise ValidationError('A salary category is required for this condition.')

    @api.constrains('amount_mode', 'amount_base', 'amount_python')
    def _check_amount_computation(self):
        for rule in self:
            if rule.amount_mode == 'percentage' and not rule.amount_base:
                raise ValidationError('A percentage base is required for this computation.')
            if rule.amount_mode == 'python' and not (rule.amount_python or '').strip():
                raise ValidationError('Python computation cannot be empty in Advanced Python mode.')
