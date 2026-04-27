# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class l10nChCafInsurance(models.Model):
    _inherit = "l10n.ch.compensation.fund"

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    insurance_company = fields.Char(required=False, store=True)
    insurance_code = fields.Char(required=True, store=True, compute=False)
    active = fields.Boolean(default=True)

    def _get_caf_rates(self, target, rate_type):
        if not self:
            return 0, 0
        for line in self.caf_line_ids:
            if line.date_from <= target and (not line.date_to or target <= line.date_to):
                return line[rate_type]
        raise UserError(_('No CAF rates found for date %s', target))
