from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ciusro', "CIUSRO")])

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_ubl_cii'
        if invoice_edi_format == 'ciusro':
            return self.env['account.edi.xml.ubl_ro']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats(self):
        # EXTENDS 'account'
        formats = super()._get_ubl_cii_formats()
        formats.append('ciusro')
        return formats

    def _get_ubl_cii_formats_by_country(self):
        # EXTENDS 'account'
        mapping = super()._get_ubl_cii_formats_by_country()
        mapping['RO'] = 'ciusro'
        return mapping
