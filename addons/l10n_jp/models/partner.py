# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Model(models.Model):
    _inherit = "res.partner"

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    def _compute_partner_company_registry_placeholder(self):
        super()._compute_partner_company_registry_placeholder()
        for partner in self:
            if partner.country_id.code == 'JP':
                partner.partner_company_registry_placeholder = '7000012050002'
