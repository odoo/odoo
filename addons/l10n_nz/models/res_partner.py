from odoo import models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        labels['NZ'] = _("NZBN")
        return labels
