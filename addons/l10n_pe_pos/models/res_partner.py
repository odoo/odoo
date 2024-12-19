# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.ondelete(at_uninstall=False)
    def _pe_unlink_except_master_data(self):
        consumidor_final_anonimo = self.env.ref("l10n_pe_pos.partner_pe_cf")
        if consumidor_final_anonimo & self:
            raise UserError(
                _(
                    "Deleting the partner %s is not allowed because it is required by the Peruvian point of sale.",
                    consumidor_final_anonimo.display_name,
                )
            )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == "PE":
            fields += ["city_id", "l10n_latam_identification_type_id", "l10n_pe_district"]
        return fields

    def _get_pos_required_partners(self, config):
        partner_ids = super()._get_pos_required_partners(config)
        if self.env.company.country_id.code == "PE":
            partner_ids = partner_ids.union({self.env.ref("l10n_pe_pos.partner_pe_cf").id})
        return partner_ids
