from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_salary_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Salary Paying Bank Account',
        groups='hr.group_hr_user',
        tracking=True,
        domain="[('partner_id', '=', company_partner_id)]",
        help='Company bank account used to pay this employee\'s salary. '
             'This is the source account the accounting team transfers from, '
             'not the employee\'s personal bank account.',
    )
    company_partner_id = fields.Many2one(
        related='company_id.partner_id',
        store=False,
    )

