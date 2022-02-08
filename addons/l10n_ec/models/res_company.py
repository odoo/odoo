from odoo import models


class ResCompany(models.Model):

    _inherit = "res.company"

    def _localization_use_documents(self):
        self.ensure_one()
        if self.country_id.code == "EC":
            return True
        return super(ResCompany, self)._localization_use_documents()
