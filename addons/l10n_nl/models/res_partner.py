# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.tools.partner_identifiers import get_non_prefixed_identifier


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_nl_sbr_ob_nummer = fields.Char(compute='_compute_l10n_nl_sbr_ob_nummer', inverse='_inverse_l10n_nl_sbr_ob_nummer')

    @api.depends('additional_identifiers')
    def _compute_l10n_nl_sbr_ob_nummer(self):
        for partner in self:
            partner.l10n_nl_sbr_ob_nummer = partner._get_additional_identifier('NL_OB')

    def _inverse_l10n_nl_sbr_ob_nummer(self):
        for partner in self:
            partner._set_additional_identifier('NL_OB', partner.l10n_nl_sbr_ob_nummer)

    @api.depends('vat')
    def _compute_available_additional_identifiers_metadata(self):
        super()._compute_available_additional_identifiers_metadata()
        for partner in self:
            metadata = partner.available_additional_identifiers_metadata
            if not metadata or 'NL_OB' not in metadata or not partner.vat:
                continue
            if ob_placeholder := get_non_prefixed_identifier('NL', partner.vat):
                partner.available_additional_identifiers_metadata = {
                    **metadata,
                    'NL_OB': {**metadata['NL_OB'], 'placeholder': ob_placeholder},
                }
