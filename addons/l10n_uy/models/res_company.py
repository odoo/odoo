# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons import account, l10n_latam_invoice_document, l10n_latam_base


class ResCompany(account.ResCompany, l10n_latam_invoice_document.ResCompany, l10n_latam_base.ResCompany):


    def _localization_use_documents(self):
        """ Uruguayan localization use documents """
        self.ensure_one()
        return self.account_fiscal_country_id.code == "UY" or super()._localization_use_documents()
