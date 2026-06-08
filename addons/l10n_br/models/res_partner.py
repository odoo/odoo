# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_br_ie_code = fields.Char(string="IE", help="State Tax Identification Number. Should contain 9-14 digits.")
    l10n_br_im_code = fields.Char(string="IM", help="Municipal Tax Identification Number")
    l10n_br_isuf_code = fields.Char(string="SUFRAMA code", help="SUFRAMA registration number.")

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'street_number', 'street_name', 'street_number2'})

        return frontend_writable_fields

    def _is_brazilean_fiscal_country(self):
        return self.env.company.account_fiscal_country_id.code == 'BR'

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo, **kwargs)
        if country_sudo.code == "BR" and self._is_brazilean_fiscal_country():
            mandatory_fields.update({'street_name', 'street2', 'street_number'})
            mandatory_fields.remove('street')

        return mandatory_fields
