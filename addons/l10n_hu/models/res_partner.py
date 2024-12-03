from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_hu_eu_vat = fields.Char(compute='_compute_l10n_hu_eu_vat')

    @api.depends('vat')
    def _compute_l10n_hu_eu_vat(self):
        for partner in self:
            if partner.country_code == 'HU' and partner.vat:
                partner.l10n_hu_eu_vat = partner._convert_hu_local_to_eu_vat(partner.vat)
            else:
                partner.l10n_hu_eu_vat = False
