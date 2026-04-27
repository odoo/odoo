# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class YearlySalaryDetail(models.TransientModel):
    _name = 'yearly.salary.detail'
    _description = 'Hr Salary Employee By Category Report'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "IN":
            raise UserError(_('You must be logged in a Indian company to use this feature'))
        return super().default_get(field_list)

    def _get_domain(self):
        self.ensure_one()
        domain = [('company_id', '=', self.env.company.id)]
        if self.department_id:
            domain += [('department_id', '=', self.department_id.id)]
        if self.job_id:
            domain += [('job_id', '=', self.job_id.id)]
        return domain

    @api.depends('department_id', 'job_id')
    def _compute_related_employee_ids(self):
        employee = self.env['hr.employee']
        for wizard in self:
            domain = wizard._get_domain()
            wizard.related_employee_ids = employee.search(domain)

    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 1)]

    year = fields.Selection(
        selection='_get_year_selection', string='Year', required=True,
        default=lambda x: str(datetime.now().year - 1))
    related_employee_ids = fields.Many2many('hr.employee', compute="_compute_related_employee_ids")
    employee_ids = fields.Many2many('hr.employee', 'payroll_emp_rel', 'payroll_id', 'employee_id', string='Employees',
        required=True, compute="_compute_employee_ids", readonly=False, store=True)
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Job Position")

    @api.depends('year', 'department_id', 'job_id')
    def _compute_employee_ids(self):
        payslip = self.env['hr.payslip']
        employee = self.env['hr.employee']
        for wizard in self:
            date_from = fields.Date.today() + relativedelta(day=1, month=1, year=int(wizard.year))
            date_to = fields.Date.today() + relativedelta(day=31, month=12, year=int(wizard.year))
            payslip_domain = [('date_from', '>=', date_from), ('date_to', '<=', date_to), ('state', '=', 'paid')]
            payslip_ids = payslip.search(payslip_domain)
            employee_domain = expression.AND([wizard._get_domain(), [('slip_ids', 'in', payslip_ids.ids)]])
            wizard.employee_ids = employee.search(employee_domain)

    def print_report(self):
        """
         To get the date and print the report
         @return: return report
        """
        self.ensure_one()
        if not self.employee_ids:
            raise UserError("There must be at least one employee available to generate a report.")
        data = {'ids': self.env.context.get('active_ids', [])}
        res = self.read()
        res = res and res[0] or {}
        data.update({'form': res})
        return self.env.ref('l10n_in_hr_payroll.action_report_hryearlysalary').with_context(active_model=self._name, discard_logo_check=True).report_action(self, data=data)
