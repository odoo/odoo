# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Model(models.Model):
    _inherit = "res.company"

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    def _compute_company_registry_placeholder(self):
        super()._compute_company_registry_placeholder()
        for company in self:
            country_code = company.country_id.code or company.account_fiscal_country_id.code
            if country_code == 'JP':
                company.company_registry_placeholder = '7000012050002'
