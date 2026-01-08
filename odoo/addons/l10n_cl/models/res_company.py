# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_cl_activity_description = fields.Char(
        string='Company Activity Description', related='partner_id.l10n_cl_activity_description', readonly=False)

    def _localization_use_documents(self):
        """ Chilean localization use documents """
        self.ensure_one()
        return self.account_fiscal_country_id.code == "CL" or super()._localization_use_documents()
