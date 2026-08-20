from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    hr_expense_ids = fields.Many2many(
        comodel_name='hr.expense',
        relation='expense_tax',
        column1='tax_id',
        column2='expense_id',
        copy=False,
        readonly=True,
    )

    @api.depends('hr_expense_ids')
    def _compute_is_used(self):
        super()._compute_is_used()
        self.sudo().search([
            ('id', 'in', self.filtered(lambda t: not t.is_used).ids),
            ('hr_expense_ids', '!=', False),
        ]).is_used = True
