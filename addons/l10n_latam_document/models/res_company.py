# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    def _localization_use_documents(self):
        """ This method is to be inherited by localizations and return
        True if localization use documents
        """
        self.ensure_one()
        return False
