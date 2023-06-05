# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_th_branch_name = fields.Char(compute="_l10n_th_get_branch_name")

    def _l10n_th_get_branch_name(self):
        for partner in self:
            if not partner.is_company or partner.country_code != 'TH':
                partner.l10n_th_branch_name = ""
            else:
                code = self.company_registry
                partner.l10n_th_branch_name = f"Branch {code}" if code else "Headquarter"
