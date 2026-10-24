from odoo import models, fields, api
from odoo.exceptions import ValidationError

TIMEOUT = 10


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('eslog', "e-SLOG 2.0")])

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'eslog':
            return self.env['account.edi.xml.eslog']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['eslog'] = {'countries': ['SI'], 'on_peppol': False}  # Is it false?
        return formats_info

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        if self.country_code == 'SI':
            return 'eslog'
        return super()._get_suggested_invoice_edi_format()
