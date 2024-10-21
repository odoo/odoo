# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('pint_anz', "PINT Australia & New Zealand")])

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'pint_anz':
            return self.env['account.edi.xml.pint_anz']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats(self):
        # EXTENDS 'account'
        formats = super()._get_ubl_cii_formats()
        formats.append('pint_anz')
        return formats

    def _get_ubl_cii_formats_by_country(self):
        # EXTENDS 'account'
        mapping = super()._get_ubl_cii_formats_by_country()
        mapping['AU'] = 'pint_anz'
        mapping['NZ'] = 'pint_anz'
        return mapping
