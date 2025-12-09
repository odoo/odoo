# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_th_branch_name = fields.Char(compute="_compute_l10n_th_branch_name")

    def _compute_l10n_th_branch_name(self):
        for partner in self:
            if not partner.is_company or partner.country_code != 'TH':
                partner.l10n_th_branch_name = ""
            else:
                code = partner.company_registry
                partner.l10n_th_branch_name = f"Branch {code}" if code and code != "00000" else "Headquarter"

    @api.constrains('company_registry')
    def _check_company_registry_l10n_th(self):
        for partner in self:
            if partner.country_code == "TH" and partner.company_registry and not re.fullmatch(r'\d{5}', partner.company_registry):
                raise ValidationError(partner.env._("The branch Code must be exactly 5 digits."))
