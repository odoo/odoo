from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = ['res.company']

    @api.constrains('company_registry')
    def _check_company_registry_ma(self):
        for record in self:
            if record.country_code == 'MA' and record.company_registry \
                and (len(record.company_registry) != 15 or not record.company_registry.isdigit()):
                raise ValidationError(_("ICE number should have exactly 15 digits."))
