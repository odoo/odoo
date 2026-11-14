# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_pa.tools.partner_identifiers import PA_ADDITIONAL_IDENTIFIERS_METADATA
from odoo.addons.l10n_pa.tools.postal_code import locate_postal_code


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pa_corregimiento = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento',
        string='Corregimiento',
        domain="[('city_id', '=?', city_id)]",
        help='Corregimientos are part of a district.',
    )
    l10n_pa_corregimiento_name = fields.Char(
        string='Corregimiento name',
        related='l10n_pa_corregimiento.name',
    )
    l10n_pa_poblado = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento.poblado',
        string='Poblado',
        domain="[('corregimiento_id', '=?', l10n_pa_corregimiento)]",
        help='Poblados are populated places within a corregimiento.',
    )
    l10n_pa_barrio = fields.Many2one(
        comodel_name='l10n_pa.res.city.corregimiento.poblado.barrio',
        string='Barrio',
        domain="[('poblado_id', '=?', l10n_pa_poblado)]",
        help='Barrios are neighborhoods within a poblado.',
    )
    l10n_pa_dv = fields.Char(
        string='DV',
        size=2,
        help='Check digit from the DGI',
    )

    @api.onchange('zip')
    def _onchange_l10n_pa_zip(self):
        if self.country_code != 'PA' or not self.zip:
            return
        location = locate_postal_code(self.env, self.zip)
        if not location:
            return {'warning': {
                'title': self.env._("Invalid postal code"),
                'message': self.env._(
                    "'%(code)s' could not be decoded, or doesn't fall within Panama.",
                    code=self.zip,
                ),
            }}
        if not location['corregimiento']:
            return {'warning': {
                'title': self.env._("Corregimiento not found"),
                'message': self.env._(
                    "The postal code is valid but doesn't fall within any known corregimiento boundary."
                ),
            }}
        self.l10n_pa_corregimiento = location['corregimiento']
        self.city_id = location['corregimiento'].city_id
        self.l10n_pa_poblado = location['poblado']
        self.l10n_pa_barrio = location['barrio']

    @api.onchange('l10n_pa_corregimiento')
    def _onchange_l10n_pa_corregimiento(self):
        if self.l10n_pa_corregimiento:
            self.city_id = self.l10n_pa_corregimiento.city_id
        if self.l10n_pa_poblado and self.l10n_pa_poblado.corregimiento_id != self.l10n_pa_corregimiento:
            self.l10n_pa_poblado = False

    @api.onchange('l10n_pa_poblado')
    def _onchange_l10n_pa_poblado(self):
        if self.l10n_pa_poblado:
            self.l10n_pa_corregimiento = self.l10n_pa_poblado.corregimiento_id
        if self.l10n_pa_barrio and self.l10n_pa_barrio.poblado_id != self.l10n_pa_poblado:
            self.l10n_pa_barrio = False

    @api.onchange('l10n_pa_barrio')
    def _onchange_l10n_pa_barrio(self):
        if self.l10n_pa_barrio:
            self.l10n_pa_poblado = self.l10n_pa_barrio.poblado_id

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
