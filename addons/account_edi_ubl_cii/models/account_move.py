# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools, Command
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import COUNTRY_EAS


class AccountMove(models.Model):
    _inherit = 'account.move'

    ubl_cii_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="UBL/CII Document",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _get_ubl_cii_builder(self):
        self.ensure_one()

        if self.country_code == 'DE':
            return self.env['account.edi.xml.ubl_de'], {'ubl_inject_pdf': True}
        if self.country_code == 'BE':
            return self.env['account.edi.xml.ubl_efff'], {'ubl_inject_pdf': True}
        if self.country_code in ('AU', 'NZ'):
            return self.env['account.edi.xml.ubl_a_nz'], {'ubl_inject_pdf': True}
        if self.country_code == 'FR':
            return self.env['account.edi.xml.cii'], {'embed_to_pdf': True, 'facturx_pdfa': True}
        if self.country_code == 'NL':
            return self.env['account.edi.xml.ubl_nl'], {'ubl_inject_pdf': True}
        if self.country_code in COUNTRY_EAS:
            return self.env['account.edi.xml.ubl_bis3'], {'ubl_inject_pdf': True}

    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        self.ensure_one()
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0':
                return self.env['account.edi.xml.ubl_bis3']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
        ubl_version = tree.find('{*}UBLVersionID')
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text == '2.1':
                return self.env['account.edi.xml.ubl_21']

    @api.model
    def _update_invoice_from_ubl_cii_xml(self, invoice, file_data, new=False):
        ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
        return ubl_cii_xml_builder._import_invoice(invoice, file_data['xml_tree'], new=new)

    @api.model
    def _get_edi_xml_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        decoder = super()._get_edi_xml_decoder(file_data, new=new)
        if decoder:
            return decoder

        ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
        if ubl_cii_xml_builder:
            return self._update_invoice_from_ubl_cii_xml
