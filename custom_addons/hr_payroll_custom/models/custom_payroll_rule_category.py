from odoo import fields, models


class CustomPayrollRuleCategory(models.Model):
    _name = 'custom.payroll.rule.category'
    _description = 'Salary Rule Category'
    _order = 'sequence, id'

    name = fields.Char(string='Category Name', required=True, translate=True)
    code = fields.Char(
        string='Code',
        required=True,
        help='Unique code for the category. '
             'Used in rule Python expressions (e.g., categories.BASIC).',
    )
    parent_id = fields.Many2one('custom.payroll.rule.category', string='Parent Category')
    sequence = fields.Integer(string='Sequence', default=10)
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
