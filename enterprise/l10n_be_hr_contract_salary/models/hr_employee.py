# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_first_contracts(self):
        self.ensure_one()
        contracts = super()._get_first_contracts()
        pfi = self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_pfi')
        return contracts.filtered(
            lambda c: c.company_id.country_id.code != 'BE' or (c.company_id.country_id.code == 'BE' and c.contract_type_id != pfi))

    @api.depends('contract_ids.state', 'contract_ids.date_start', 'contract_ids.contract_type_id')
    def _compute_first_contract_date(self):
        return super()._compute_first_contract_date()
