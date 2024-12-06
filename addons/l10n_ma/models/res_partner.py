from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('company_registry')
    def _check_company_registry_ma(self):
        for record in self:
            if record.country_code == 'MA' and record.company_registry and (len(record.company_registry) != 15 or not record.company_registry.isdigit()):
                raise ValidationError(_("ICE number should have exactly 15 digits."))

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        labels['MA'] = _("ICE")
        return labels
