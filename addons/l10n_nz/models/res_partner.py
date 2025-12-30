from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        labels['NZ'] = self.env._("NZBN")
        return labels
