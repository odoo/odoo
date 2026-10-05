# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models
from odoo.addons.l10n_pa.tools.partner_identifiers import PA_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pa_corregimiento = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento',
        string='Corregimiento',
        ui_domain="[('city_id', '=?', city_id)]",
        help='Corregimientos are part of a district.',
    )
    l10n_pa_corregimiento_name = fields.Char(
        string='Corregimiento name',
        related='l10n_pa_corregimiento.name',
    )
    l10n_pa_dv = fields.Char(
        string='DV',
        size=2,
        help='Check digit from the DGI',
    )
    l10n_pa_vat_is_cedula = fields.Boolean(compute='_compute_l10n_pa_vat_is_cedula')

    @api.depends('vat', 'country_code')
    def _compute_l10n_pa_vat_is_cedula(self):
        for partner in self:
            # cédula of province 1-13 (AV, PI included), PE, E or N, NT left out as legal NTs exist
            partner.l10n_pa_vat_is_cedula = bool(
                partner.country_code == 'PA'
                and partner.vat
                and re.fullmatch(r'((1[0-3]|[1-9])(AV|PI)?|PE|E|N)-[0-9]+-[0-9]+', partner.vat.strip(), re.IGNORECASE),
            )

    @api.onchange('l10n_pa_corregimiento')
    def _onchange_l10n_pa_corregimiento(self):
        if self.l10n_pa_corregimiento:
            self.city_id = self.l10n_pa_corregimiento.city_id

    @api.onchange('city_id')
    def _onchange_l10n_pa_city_id(self):
        if self.city_id and self.l10n_pa_corregimiento.city_id and self.l10n_pa_corregimiento.city_id != self.city_id:
            self.l10n_pa_corregimiento = False

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super()._formatting_address_fields() + ['l10n_pa_corregimiento_name']

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {
            **super()._get_all_additional_identifiers_metadata(),
            **PA_ADDITIONAL_IDENTIFIERS_METADATA,
        }
