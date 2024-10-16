from odoo import models
from odoo.addons import account, l10n_latam_invoice_document, l10n_latam_base


class ResCompany(l10n_latam_invoice_document.ResCompany, l10n_latam_base.ResCompany, account.ResCompany):


    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "EC" or super(ResCompany, self)._localization_use_documents()
