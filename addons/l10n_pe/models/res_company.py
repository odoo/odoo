# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import account, l10n_latam_invoice_document, base_vat, l10n_latam_base


class ResCompany(base_vat.ResCompany, l10n_latam_base.ResCompany, l10n_latam_invoice_document.ResCompany, account.ResCompany):

    def _localization_use_documents(self):
        # OVERRIDE
        self.ensure_one()
        return self.account_fiscal_country_id.code == "PE" or super()._localization_use_documents()
