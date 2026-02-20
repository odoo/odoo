# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_br_ie_code = fields.Char(string="IE", help="State Tax Identification Number. Should contain 9-14 digits.")
    l10n_br_im_code = fields.Char(string="IM", help="Municipal Tax Identification Number")
    l10n_br_isuf_code = fields.Char(string="SUFRAMA code", help="SUFRAMA registration number.")

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update({'city_id', 'street_number', 'street_name', 'street_number2'})

        return frontend_writable_fields

    @api.depends("l10n_latam_identification_type_id")
    def _compute_is_company(self):
        cnpj = self.env.ref('l10n_br.cnpj', raise_if_not_found=False)
        l10n_br_partners = self.filtered(lambda p: p.country_code == 'BR')
        if cnpj:
            # Partners with CNPJ are legal entities => companies
            l10n_br_companies = l10n_br_partners.filtered(lambda p: p.l10n_latam_identification_type_id == cnpj)
            l10n_br_companies.is_company = True
            (l10n_br_partners - l10n_br_companies).is_company = False

        super(ResPartner, self - l10n_br_partners)._compute_is_company()
