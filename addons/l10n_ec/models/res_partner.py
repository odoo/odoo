# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def check_vat_ec(self, vat):
        if self.l10n_latam_identification_type_id.is_vat:
            if self.l10n_latam_identification_type_id.name == 'Ced':
                return self.is_valid_ci_ec(vat)
            elif self.l10n_latam_identification_type_id.name == 'RUC' and vat != '9999999999999':
                return self.is_valid_ruc_ec(vat)
        return True

    def _get_complete_address(self):
        self.ensure_one()
        partner_id = self
        address = ""
        if partner_id.street:
            address += partner_id.street + ", "
        if partner_id.street2:
            address += partner_id.street2 + ", "
        if partner_id.city:
            address += partner_id.city + ", "
        if partner_id.state_id:
            address += partner_id.state_id.name + ", "
        if partner_id.zip:
            address += "(" + partner_id.zip + ") "
        if partner_id.country_id:
            address += partner_id.country_id.name
        return address
