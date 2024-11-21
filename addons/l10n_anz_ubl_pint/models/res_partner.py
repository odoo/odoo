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

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['pint_anz'] = {'countries': ['AU', 'NZ'], 'on_peppol': True, 'sequence': 90}  # has priority over UBL_ANZ from 'account_edi_ubl_cii'
        return formats_info
