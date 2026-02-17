from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(
        selection_add=[
            ('ubl_fr_en16931', "PDP EN16931"),
            ('ubl_fr_en16931_extended', "PDP EN16931 Extended"),
            ('cii_fr_cius', "PDP France CIUS"),
            ('cii_fr_cius_extended', "PDP France CIUS Extended"),
        ]
    )

    def _get_edi_builder(self, invoice_edi_format):
        if invoice_edi_format == 'ubl_fr_en16931':
            return self.env['account.edi.xml.ubl_fr_pdp_en16931']
        if invoice_edi_format == 'ubl_fr_en16931_extended':
            return self.env['account.edi.xml.ubl_fr_pdp_en16931_extended']
        if invoice_edi_format == 'cii_fr_cius':
            return self.env['account.edi.xml.cii_france_cius']
        if invoice_edi_format == 'cii_fr_cius_extended':
            return self.env['account.edi.xml.cii_france_cius_extended']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_fr_en16931'] = {'countries': ['FR'], 'on_peppol': True}
        formats_info['ubl_fr_en16931_extended'] = {'countries': ['FR'], 'on_peppol': True}
        formats_info['cii_fr_cius'] = {'countries': ['FR'], 'on_peppol': True}
        formats_info['cii_fr_cius_extended'] = {'countries': ['FR'], 'on_peppol': True}
        return formats_info
