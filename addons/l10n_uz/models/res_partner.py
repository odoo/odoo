from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat', 'commercial_partner_id')
    def _compute_is_company(self):
        l10n_uz_partners = self.filtered(lambda partner: partner.country_code == 'UZ' and partner.has_vat)
        for partner in l10n_uz_partners:
            partner.is_company = bool(len(partner.vat) == 9 and partner.commercial_partner_id == partner)

        super(ResPartner, self - l10n_uz_partners)._compute_is_company()
