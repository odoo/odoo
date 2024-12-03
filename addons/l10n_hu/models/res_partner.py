from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_hu_eu_vat = fields.Char(compute='_compute_l10n_hu_eu_vat')

    @api.depends('vat')
    def _compute_l10n_hu_eu_vat(self):
        hu_vat_partners = self.filtered(lambda p: p.country_code == 'HU' and p.vat)
        for partner in hu_vat_partners:
            partner.l10n_hu_eu_vat = partner._convert_hu_local_to_eu_vat(partner.vat)
        (self - hu_vat_partners).l10n_hu_eu_vat = False
