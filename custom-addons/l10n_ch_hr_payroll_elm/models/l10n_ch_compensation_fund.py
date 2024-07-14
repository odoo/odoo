# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError


class l10nChAccidentInsurance(models.Model):
    _inherit = "l10n.ch.compensation.fund"

    insurance_company = fields.Char(required=True, store=True)
    insurance_code = fields.Char(required=True, store=True, compute=False)

    def _get_caf_rates(self, target, rate_type):
        if not self:
            return 0, 0
        for line in self.caf_line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line[rate_type]
        raise UserError(_('No CAF rates found for date %s', target))


class l10nChCompensationFundLine(models.Model):
    _inherit = 'l10n.ch.compensation.fund.line'

    employee_rate = fields.Float(string="Employee Rate (%)", digits='Payroll Rate', default=0.0)
    company_rate = fields.Float(string="Company Rate (%)", digits='Payroll Rate', default=0.421)
