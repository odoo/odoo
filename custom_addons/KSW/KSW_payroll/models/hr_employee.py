from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _rec_names_search = [
        'name',
        'ssnid',
        'identification_id',
        'barcode',
        'work_email',
        'mobile_phone',
    ]

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
    x_employee_no = fields.Char(
        string='Employee No.',
        index=True,
        groups='hr.group_hr_user',
        help='Internal employee number used by HR.',
    )
    x_payslip_export_order = fields.Integer(
        string='Payslip File Order',
        default=0,
        index=True,
        groups='hr.group_hr_user',
        help='Lower numbers are exported first in payroll TXT/Excel files.',
    )
    company_partner_id = fields.Many2one(
        related='company_id.partner_id',
        store=False,
    )

