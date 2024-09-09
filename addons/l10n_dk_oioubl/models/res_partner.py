from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('oioubl_201', "OIOUBL 2.01")])

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'oioubl_201':
            return self.env['account.edi.xml.oioubl_201']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats(self):
        # EXTENDS 'account'
        formats = super()._get_ubl_cii_formats()
        formats.append('oioubl_201')
        return formats

    def _get_ubl_cii_formats_by_country(self):
        # EXTENDS 'account'
        mapping = super()._get_ubl_cii_formats_by_country()
        mapping['DK'] = 'oioubl_201'
        return mapping
