from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _localization_use_documents(self):
        """This method is to be inherited by localizations and return True if localization use documents"""
        self.check_singleton()
        return False
