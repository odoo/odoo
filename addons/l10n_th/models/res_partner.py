# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_th_branch_name = fields.Char(compute="_compute_l10n_th_branch_name")

    def _compute_l10n_th_branch_name(self):
        for partner in self:
            # TODO: Check with accounting team
            if not partner.vat or partner.country_code != 'TH':
                partner.l10n_th_branch_name = ""
            else:
                code = partner.company_registry
                partner.l10n_th_branch_name = f"Branch {code}" if code else "Headquarter"
