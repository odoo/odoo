# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('pint_my', "PINT Malaysia")])
    sst_registration_number = fields.Char(
        string="SST",
        help="Malaysian Sales and Service Tax Number",
    )
    ttx_registration_number = fields.Char(
        string="TTx",
        help="Malaysian Tourism Tax Number",
    )

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'pint_my':
            return self.env['account.edi.xml.pint_my']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['pint_my'] = {'countries': ['MY'], 'on_peppol': True}
        return formats_info
