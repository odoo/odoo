from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_siret = fields.Char(compute='_compute_l10n_fr_siret', inverse='_inverse_l10n_fr_siret')
    l10n_fr_siren = fields.Char(compute='_compute_l10n_fr_siren', inverse='_inverse_l10n_fr_siren')

    @api.depends('additional_identifiers')
    def _compute_l10n_fr_siret(self):
        for partner in self:
            partner.l10n_fr_siret = partner._get_additional_identifier('FR_SIRET')

    def _inverse_l10n_fr_siret(self):
        for partner in self:
            partner._set_additional_identifier('FR_SIRET', partner.l10n_fr_siret)

    @api.depends('additional_identifiers')
    def _compute_l10n_fr_siren(self):
        for partner in self:
            # Will deduce SIREN from SIRET if available
            partner.l10n_fr_siren = partner._get_all_identifiers(enrich=True).get('FR_SIREN')

    def _inverse_l10n_fr_siren(self):
        for partner in self:
            partner._set_additional_identifier('FR_SIREN', partner.l10n_fr_siren)
