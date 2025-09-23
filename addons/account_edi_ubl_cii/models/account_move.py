import binascii

from base64 import b64decode
from contextlib import suppress
from lxml import etree

from odoo import _, api, fields, models, Command


class AccountMove(models.Model):
    _inherit = 'account.move'

    ubl_cii_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Attachment",
        compute=lambda self: self._compute_linked_attachment_id('ubl_cii_xml_id', 'ubl_cii_xml_file'),
        depends=['ubl_cii_xml_file']
    )
    ubl_cii_xml_file = fields.Binary(
        attachment=True,
        string="UBL/CII File",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_invoice_download_ubl(self):
        if invoices_with_ubl := self.filtered('ubl_cii_xml_id'):
            return {
                'type': 'ir.actions.act_url',
                'url': f'/account/download_invoice_documents/{",".join(map(str, invoices_with_ubl.ids))}/ubl',
                'target': 'download',
            }
        return False

    # -------------------------------------------------------------------------
    # BUSINESS
    # -------------------------------------------------------------------------

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append("ubl_cii_xml_file")
        return fields_list

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        # EXTENDS account
        if filetype == 'ubl':
            if ubl_attachment := self.ubl_cii_xml_id:
                return {
                    'filename': ubl_attachment.name,
                    'filetype': 'xml',
                    'content': ubl_attachment.raw,
                }
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def get_extra_print_items(self):
        print_items = super().get_extra_print_items()
        if self.ubl_cii_xml_id:
            print_items.append({
                'key': 'download_ubl',
                'description': _('XML UBL'),
                **self.action_invoice_download_ubl(),
            })
        return print_items

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        ubl_version = tree.find('{*}UBLVersionID')
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text in ('2.1', '2.2', '2.3'):
                return self.env['account.edi.xml.ubl_21']
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0':
                return self.env['account.edi.xml.ubl_a_nz']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0':
                return self.env['account.edi.xml.ubl_sg']
            if 'urn:cen.eu:en16931:2017' in customization_id.text:
                return self.env['account.edi.xml.ubl_bis3']

    @api.model
    def _ubl_parse_attached_document(self, tree):
        """
        In UBL, an AttachedDocument file is a wrapper around multiple different UBL files.
        According to the specifications the original document is stored within the top most
        Attachment node either as an Attachment/EmbeddedDocumentBinaryObject or (in special cases)
        a CDATA string stored in Attachment/ExternalReference/Description.

        We must parse this before passing the original file to the decoder to figure out how best
        to handle it.
        """
        attachment_node = tree.find('{*}Attachment')
        if attachment_node is None:
            return tree

        attachment_binary_data = attachment_node.find('./{*}EmbeddedDocumentBinaryObject')
        if attachment_binary_data is not None \
                and attachment_binary_data.attrib.get('mimeCode') in ('application/xml', 'text/xml'):
            with suppress(etree.XMLSyntaxError, binascii.Error):
                text = b64decode(attachment_binary_data.text)
                return etree.fromstring(text)

        external_reference = attachment_node.find('./{*}ExternalReference')
        if external_reference is not None:
            description = external_reference.findtext('./{*}Description')
            mime_code = external_reference.findtext('./{*}MimeCode')

            if description and mime_code in ('application/xml', 'text/xml'):
                with suppress(etree.XMLSyntaxError):
                    return etree.fromstring(description.encode('utf-8'))
        return tree

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'xml':
            if etree.QName(file_data['xml_tree']).localname == 'AttachedDocument':
                file_data['xml_tree'] = self._ubl_parse_attached_document(file_data['xml_tree'])
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is not None:
                return ubl_cii_xml_builder._import_invoice_ubl_cii

        return super()._get_edi_decoder(file_data, new=new)

    def _need_ubl_cii_xml(self, ubl_cii_format):
        self.ensure_one()
        return not self.ubl_cii_xml_id \
            and self.is_sale_document() \
            and ubl_cii_format in self.env['res.partner']._get_ubl_cii_formats()

    @api.model
    def _get_line_vals_list(self, lines_vals):
        """ Get invoice line values list.

        param list line_vals: List of values [name, qty, price, tax].
        :return: List of invoice line values.
        """
        return [{
            'sequence': 0,  # be sure to put these lines above the 'real' invoice lines
            'name': name,
            'quantity': quantity,
            'price_unit': price_unit,
            'tax_ids': [Command.set(tax_ids)],
        } for name, quantity, price_unit, tax_ids in lines_vals]

    def _get_specific_tax(self, name, amount_type, amount, tax_type):
        AccountMoveLine = self.env['account.move.line']
        if hasattr(AccountMoveLine, '_predict_specific_tax'):
            # company check is already done in the prediction query
            predicted_tax_id = AccountMoveLine._predict_specific_tax(
                self, name, self.partner_id, amount_type, amount, tax_type,
            )
            return self.env['account.tax'].browse(predicted_tax_id)
        return self.env['account.tax']
