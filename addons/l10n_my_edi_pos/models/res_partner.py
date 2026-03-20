from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'l10n_my_edi_malaysian_tin'})

        return frontend_writable_fields

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        field_names = super()._get_mandatory_address_fields(country_sudo, **kwargs)

        if self.env.company.country_code == country_sudo.code == 'MY':
            field_names.add('state_id')

        return field_names
