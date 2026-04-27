# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ytd_balance_ids = fields.One2many("l10n_au.payslip.ytd", "employee_id", string="YTD Balances", groups="hr.group_hr_user")

    def _get_fiscal_year_data(self, date_start: date, date_end: date, finalised=False):
        self.ensure_one()
        payslip_ids = self.slip_ids.filtered_domain([
            ('date_from', '>=', date_start),
            ('date_from', '<=', date_end),
            ('state', 'in', ('done', 'paid')),
            ('l10n_au_finalised', '=', finalised)
        ])

        ytd_balance_ids = self.env['l10n_au.payslip.ytd'].search([
            ('employee_id', '=', self.id),
            ('start_date', '=', date_start),  # Start date is always set to the start of fiscal year
            ('finalised', '=', finalised)
        ])

        return payslip_ids.ids, ytd_balance_ids.ids
