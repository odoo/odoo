# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_th_branch_name = fields.Char(compute="_l10n_th_get_branch_name")

    def _l10n_th_get_branch_name(self):
        for rec in self:
            if not rec.is_company:
                rec.l10n_th_branch_name = ""
            code = self.company_registry
            rec.l10n_th_branch_name = f"Branch {code}" if code else "Headquarter"
