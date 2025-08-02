from odoo import fields, models


class HrExpense(models.Model):
    _name = 'hr.expense.group'
    _description = 'Expense Group'
    _order = 'sequence desc'

    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence', default=100)
    parent_id = fields.Many2one(
        'hr.expense.group',
        string='Super Group',
        help='Expense group containing this one',
    )
    expense_ids = fields.Many2many(
        comodel_name='hr.expense',
        string='Expenses',
        help='Expenses grouped',
    )
