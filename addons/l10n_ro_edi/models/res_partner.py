import stdnum

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ciusro', "Romania (CIUS RO)")])

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_ubl_cii'
        if invoice_edi_format == 'ciusro':
            return self.env['account.edi.xml.ubl_ro']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ciusro'] = {'countries': ['RO']}
        return formats_info

    def _compute_is_company(self):
        l10n_ro_partners = self.filtered(lambda p: p.vat and p.country_code == 'RO')
        for partner in l10n_ro_partners:
            partner.is_company = False
            _, vat_number = self._split_vat(partner.vat)
            if not self._check_tin1_ro_natural_persons.match(vat_number)\
                and not self._check_tin2_ro_natural_persons.match(vat_number)\
                and stdnum.util.get_cc_module('ro', 'vat').is_valid(vat_number):
                partner.is_company = True

        super(ResPartner, self - l10n_ro_partners)._compute_is_company()
