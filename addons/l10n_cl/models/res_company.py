# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons import account, l10n_latam_invoice_document, base_vat, l10n_latam_base


class ResCompany(base_vat.ResCompany, l10n_latam_base.ResCompany, l10n_latam_invoice_document.ResCompany, account.ResCompany):

    l10n_cl_activity_description = fields.Char(
        string='Company Activity Description', related='partner_id.l10n_cl_activity_description', readonly=False)

    def _localization_use_documents(self):
        """ Chilean localization use documents """
        self.ensure_one()
        return self.account_fiscal_country_id.code == "CL" or super()._localization_use_documents()
