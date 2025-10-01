from odoo import _, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        labels['FI'] = _('Business ID')
        return labels
