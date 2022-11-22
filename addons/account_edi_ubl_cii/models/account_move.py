# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    ubl_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="UBL Attachment",
        compute=lambda self: self._compute_linked_attachment_id('ubl_xml_id', 'ubl_xml_file'),
        depends=['ubl_xml_file']
    )
    ubl_xml_file = fields.Binary(
        attachment=True,
        string="UBL File",
        copy=False,
    )

    cii_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="CII Attachment",
        compute=lambda self: self._compute_linked_attachment_id('cii_xml_id', 'cii_xml_file'),
        depends=['cii_xml_file']
    )
    cii_xml_file = fields.Binary(
        comodel_name='ir.attachment',
        string="CII File",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
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

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'xml':
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is not None:
                return ubl_cii_xml_builder._import_invoice_ubl_cii

        return super()._get_edi_decoder(file_data, new=new)
