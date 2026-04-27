# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'
    _description = 'Salary Structure'

    l10n_mx_schedule_pay = fields.Selection(related='type_id.l10n_mx_default_schedule_pay')
    country_code = fields.Char(related='country_id.code', depends=['country_id'], readonly=True)
