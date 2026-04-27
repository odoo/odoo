# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class YearlySalaryDetail(models.TransientModel):
    _name = 'salary.register.wizard'
    _description = 'Salary Register'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "IN":
            raise UserError(_('You must be logged in a Indian company to use this feature'))
        return super().default_get(field_list)

    def _get_default_date_from(self):
        return fields.Date.today() + relativedelta(day=1, month=1)

    def _get_default_date_to(self):
        return fields.Date.today() + relativedelta(day=31)

    def _get_employee_ids_domain(self):
        employees = self.env['hr.payslip'].search([('state', '=', 'paid')]).employee_id.filtered(lambda e: e.company_id.country_id.code == "IN").ids
        return [('id', 'in', employees)]

    def _get_struct_id_domain(self):
        return ['|', ('country_id', '=', self.env.ref('base.in').id), ('country_id', '=', False)]

    employee_ids = fields.Many2many('hr.employee', 'emp_register_rel', 'register_id', 'employee_id', string='Employees', required=True,
                                    compute="_compute_employee_ids", store=True, readonly=False, domain=_get_employee_ids_domain)
    date_from = fields.Date(string='Start Date', required=True, default=_get_default_date_from)
    date_to = fields.Date(string='End Date', required=True, default=_get_default_date_to)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', domain=_get_struct_id_domain)

    def action_export_xlsx(self):
        self.ensure_one()
        return {
            'name': _('Export Salary Register Report into XLSX'),
            'type': 'ir.actions.act_url',
            'url': '/export/salary-register/%s' % (self.id),
        }

    @api.depends('date_from', 'date_to', 'struct_id')
    def _compute_employee_ids(self):
        for record in self:
            date_from = record.date_from or self._get_default_date_from()
            date_to = record.date_to or self._get_default_date_to()
            domain = [('date_from', '>=', date_from), ('date_to', '<=', date_to), ('state', '=', 'paid'), ('company_id', 'in', self.env.companies.ids)]
            if record.struct_id:
                domain.append(('struct_id', '=', record.struct_id.id))
            payslips = record.env['hr.payslip'].search(domain)
            record.employee_ids = payslips.employee_id.filtered(lambda e: e.company_id.country_id.code == "IN")
