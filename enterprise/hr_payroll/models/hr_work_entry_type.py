# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'
    _description = 'HR Work Entry Type'

    _sql_constraints = [
        ('is_unforeseen_is_leave', 'check (is_unforeseen IS NOT TRUE OR (is_leave = TRUE and is_unforeseen = TRUE))', 'A unforeseen absence must be a leave.')
    ]

    is_unforeseen = fields.Boolean(default=False, string="Unforeseen Absence", help="The Work Entry checked as Unforeseen Absence will be counted in absenteeism at work report.")
    round_days = fields.Selection(
        [('NO', 'No Rounding'),
         ('HALF', 'Half Day'),
         ('FULL', 'Day')
        ], string="Rounding", required=True, default='NO',
        help="When the work entry is displayed in the payslip, the value is rounded accordingly.")
    round_days_type = fields.Selection(
        [('HALF-UP', 'Closest'),
         ('UP', 'Up'),
         ('DOWN', 'Down')
        ], string="Round Type", required=True, default='DOWN',
        help="Way of rounding the work entry type.")
    unpaid_structure_ids = fields.Many2many(
        'hr.payroll.structure', 'hr_payroll_structure_hr_work_entry_type_rel',
        string="Unpaid in Structures Types",
        help="The work entry won’t grant any money to employee in payslip.")
    current_companies_country_codes = fields.Char(string="country codes", compute='_compute_current_companies_country_codes')

    @api.depends_context('allowed_company_ids')
    def _compute_current_companies_country_codes(self):
        self.current_companies_country_codes = self.env.companies.mapped('country_id.code')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_work_entry_type(self):
        if self and self.env.uid != SUPERUSER_ID:
            raise UserError(_("You cannot delete work entry type(s). Instead archive it."))
