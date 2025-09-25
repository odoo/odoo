# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('tw_ecpay', "ECPay")])

    def _compute_is_company(self):
        l10n_tw_partners = self.filtered(lambda p: p.country_code == 'TW')
        for partner in l10n_tw_partners:
            partner.is_company = False
            if not partner._is_vat_void(partner.vat) and partner.vat.isdigit() and len(partner.vat) == 8:
                partner.is_company = True

        super(ResPartner, self - l10n_tw_partners)._compute_is_company()
