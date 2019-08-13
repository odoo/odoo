# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_cl_rut = fields.Char(related='partner_id.l10n_cl_rut', readonly=True)
    l10n_cl_rut_dv = fields.Char(related='partner_id.l10n_cl_rut_dv', readonly=True)

    def _localization_use_documents(self):
        """ Chilean localization use documents """
        self.ensure_one()
        return True if self.country_id == self.env.ref(
            'base.cl') else super()._localization_use_documents()
