# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.tools import ormcache
from odoo.exceptions import UserError


class HrSalaryRuleParameter(models.Model):
    _inherit = 'hr.rule.parameter'

    @api.model
    @ormcache('code', 'date', 'tuple(self.env.context.get("allowed_company_ids", []))')
    def _get_parameter_from_code(self, code, date=None, raise_if_not_found=True):
        if not code.startswith('l10n_ch_withholding_tax_rates_'):
            return super()._get_parameter_from_code(code, date=date, raise_if_not_found=raise_if_not_found)
        try:
            res = super()._get_parameter_from_code(code, date=date, raise_if_not_found=raise_if_not_found)
        except UserError as e:
            raise UserError(_("No tax rates found for the employee canton. Make sure you've actually imported using the wizard under Configuration -> Swiss -> Import Tax Rates")) from e
        return res
