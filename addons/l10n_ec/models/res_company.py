from odoo import models
from odoo.addons import base


class ResCompany(models.Model, base.ResCompany):


    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "EC" or super(ResCompany, self)._localization_use_documents()
