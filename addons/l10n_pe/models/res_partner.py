# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pe_district = fields.Many2one(
        'l10n_pe.res.city.district', string='District',
        help='Districts are part of a province or city.')
    l10n_pe_district_name = fields.Char(string='District name', related='l10n_pe_district.name')

    @api.onchange('l10n_pe_district')
    def _onchange_l10n_pe_district(self):
        if self.l10n_pe_district:
            self.city_id = self.l10n_pe_district.city_id

    @api.onchange('city_id')
    def _onchange_l10n_pe_city_id(self):
        if self.city_id and self.l10n_pe_district.city_id and self.l10n_pe_district.city_id != self.city_id:
            self.l10n_pe_district = False

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super()._formatting_address_fields() + ['l10n_pe_district_name']
