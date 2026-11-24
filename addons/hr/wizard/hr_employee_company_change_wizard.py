# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date


class HrEmployeeCompanyChangeWizard(models.TransientModel):
    _name = 'hr.employee.company.change.wizard'
    _description = 'Move Employee to a New Company Wizard'

    version_id = fields.Many2one('hr.version', required=True, readonly=True)
    employee_id = fields.Many2one(related='version_id.employee_id')
    company_id = fields.Many2one('res.company', string='New Company', required=True)
    min_date = fields.Date(compute='_compute_min_date')
    date_version = fields.Date(
        string='Effective Date', compute='_compute_date_version', store=True, readonly=False, required=True, precompute=True)

    @api.depends('version_id')
    def _compute_min_date(self):
        # after the payslips of all the versions of the employee
        for wizard in self:
            wizard.min_date = max(filter(None, (
                version._get_company_change_date() for version in wizard.version_id.employee_id.version_ids
            )), default=False)

    @api.depends('min_date')
    def _compute_date_version(self):
        # the end of the current contract if it has one, the first day after the payslips otherwise
        for wizard in self:
            dates = [wizard.min_date] if wizard.min_date else []
            if wizard.version_id.contract_date_end:
                dates.append(wizard.version_id.contract_date_end + relativedelta(days=1))
            wizard.date_version = max(dates, default=False)

    def action_confirm(self):
        self.ensure_one()
        if self.min_date and self.date_version < self.min_date:
            raise ValidationError(self.env._(
                "The effective date must be after the period covered by payslips: %s at the earliest.",
                format_date(self.env, self.min_date)))
        self.employee_id._move_to_company(self.company_id, self.date_version)
        return {'type': 'ir.actions.act_window_close'}
