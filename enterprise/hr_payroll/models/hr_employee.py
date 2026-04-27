# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    currency_id = fields.Many2one(
        "res.currency",
        string='Currency',
        related='company_id.currency_id')
    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True, groups="hr_payroll.group_hr_payroll_user")
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count', groups="hr_payroll.group_hr_payroll_user")
    registration_number = fields.Char('Registration Number of the Employee', groups="hr.group_hr_user", copy=False)
    salary_attachment_ids = fields.Many2many(
        'hr.salary.attachment',
        string='Salary Attachments',
        groups="hr_payroll.group_hr_payroll_user")
    salary_attachment_count = fields.Integer(
        compute='_compute_salary_attachment_count', string="Salary Attachment Count",
        groups="hr_payroll.group_hr_payroll_user")
    mobile_invoice = fields.Binary(string="Mobile Subscription Invoice", groups="hr_contract.group_hr_contract_manager")
    sim_card = fields.Binary(string="SIM Card Copy", groups="hr_contract.group_hr_contract_manager")
    internet_invoice = fields.Binary(string="Internet Subscription Invoice", groups="hr_contract.group_hr_contract_manager")
    is_non_resident = fields.Boolean(string='Non-resident', help='If recipient lives in a foreign country', groups="hr.group_hr_user")
    disabled = fields.Boolean(string="Disabled", help="If the employee is declared disabled by law", groups="hr.group_hr_user", tracking=True)
    structure_type_id = fields.Many2one(string="Salary Structure Type", related="contract_id.structure_type_id", groups="hr.group_hr_user")

    _sql_constraints = [
        ('unique_registration_number', 'UNIQUE(registration_number, company_id)', 'No duplication of registration numbers is allowed')
    ]

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)

    def _compute_salary_attachment_count(self):
        for employee in self:
            employee.salary_attachment_count = len(employee.salary_attachment_ids)

    @api.model
    def _get_account_holder_employees_data(self):
        # as acc_type isn't stored we can not use a domain to retrieve the employees
        # bypass orm for performance, we only care about the employee id anyway

        # return nothing if user has no right to either employee or bank partner
        if (not self.browse().has_access('read') or
                not self.env['res.partner.bank'].has_access('read')):
            return []

        self.env.cr.execute('''
            SELECT emp.id,
                   acc.acc_number,
                   acc.allow_out_payment
              FROM hr_employee emp
         LEFT JOIN res_partner_bank acc
                ON acc.id=emp.bank_account_id
              JOIN hr_contract con
                ON con.employee_id=emp.id
             WHERE emp.company_id IN %s
               AND emp.active=TRUE
               AND con.state='open'
               AND emp.bank_account_id is not NULL
        ''', (tuple(self.env.companies.ids),))

        return self.env.cr.dictfetchall()
