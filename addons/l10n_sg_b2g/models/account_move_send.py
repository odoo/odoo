# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from lxml import etree

from odoo import api, models
from odoo.tools import cleanup_xml_node

from odoo.addons.account.tools import dict_to_xml

SG_B2G_ALLOWED_ATTACHMENT_MIMETYPES = {
    'image/bmp',
    'image/gif',
    'image/jpeg',
    'application/pdf',
    'image/png',
}

SG_B2G_MAX_ATTACHMENT_SIZE = 1_000_000  # 1MB


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        """
        OVERRIDE of `account.move.send._postprocess_invoice_ubl_xml`:
        - Validate attachments for SG B2G e-invoices before embedding them in the UBL XML.
        - Skip automatically embedding move.invoice_pdf_report_id.
        """
        if invoice_data.get('ubl_cii_xml_options', {}).get('ubl_cii_format') != 'ubl_sg_b2g':
            super()._postprocess_invoice_ubl_xml(invoice, invoice_data)
            return

        errors = self._validate_sg_b2g_attachments(invoice, invoice_data)
        if errors:
            invoice_data['error'] = {
                'error_title': self.env._("Errors occurred while validating SG B2G e-invoice attachments:"),
                'errors': errors,
            }
            return

        tree = etree.fromstring(invoice_data['ubl_cii_xml_attachment_values']['raw'])

        localname = etree.QName(tree).localname
        anchor_xpath = {
            'Invoice': "//*[local-name()='ProjectReference' or local-name()='Signature' or local-name()='AccountingSupplierParty']",
            'CreditNote': "//*[local-name()='StatementDocumentReference' or local-name()='OriginatorDocumentReference' or local-name()='Signature' or local-name()='AccountingSupplierParty']",
            'DebitNote': "//*[local-name()='Signature' or local-name()='AccountingSupplierParty']",
        }.get(localname)

        anchor_elements = tree.xpath(anchor_xpath)

        if not anchor_elements:
            return

        anchor_index = tree.index(anchor_elements[0])

        edi_model = invoice_data["ubl_cii_xml_options"]["builder"]
        vals = {'invoice': invoice}
        edi_model._add_invoice_config_vals(vals)
        nsmap = edi_model._get_document_nsmap(vals)

        attachments_to_embed = [
            {
                'filename': attachment.name,
                'raw': attachment.raw,
                'mimetype': attachment.mimetype,
            }
            for attachment in self._get_ubl_available_attachments(
                invoice_data['mail_attachments_widget'],
                invoice_data['invoice_edi_format'],
            )[0]
        ] if invoice_data.get('mail_attachments_widget') else []

        for attachment_values in attachments_to_embed:
            additional_document_reference_node = {
                '_tag': 'cac:AdditionalDocumentReference',
                'cbc:ID': {'_text': attachment_values['filename']},
                'cbc:DocumentTypeCode': attachment_values.get('document_type_node'),
                'cac:Attachment': {
                    'cbc:EmbeddedDocumentBinaryObject': {
                        '_text': base64.b64encode(attachment_values['raw']).decode(),
                        'mimeCode': attachment_values['mimetype'],
                        'filename': attachment_values['filename'],
                    },
                },
            }
            tree.insert(anchor_index, dict_to_xml(additional_document_reference_node, nsmap=nsmap))

        invoice_data['ubl_cii_xml_attachment_values']['raw'] = etree.tostring(
            cleanup_xml_node(tree), xml_declaration=True, encoding='UTF-8',
        )

    @api.model
    def _validate_sg_b2g_attachments(self, invoice, invoice_data):
        """Validate attachment constraints for SG B2G e-invoices.

        AGD B2G rules:
        - Only 1 attachment is allowed per e-invoice.
        - Acceptable formats: BMP, GIF, JPEG, JPG, PDF, PNG.
        - Maximum file size: 1MB per attachment.
        """
        available_attachments, not_supported_attachments = self._get_ubl_available_attachments(
            invoice_data.get('mail_attachments_widget'),
            invoice_data.get('invoice_edi_format'),
        )
        attachments_to_embed = [
            {'raw': attachment.raw, 'mimetype': attachment.mimetype}
            for attachment in available_attachments + not_supported_attachments
        ]

        errors = []

        if len(attachments_to_embed) > 1:
            errors.append(self.env._(
                "Only 1 attachment is allowed per SG B2G e-invoice, but %(count)s were found.",
                count=len(attachments_to_embed),
            ))

        for att in attachments_to_embed:
            if att['mimetype'] not in SG_B2G_ALLOWED_ATTACHMENT_MIMETYPES:
                errors.append(self.env._(
                    "Attachment format '%(mimetype)s' is not allowed for SG B2G e-invoices."
                    " Acceptable formats: BMP, GIF, JPEG, JPG, PDF, PNG.",
                    mimetype=att['mimetype'],
                ))

            if len(att['raw']) > SG_B2G_MAX_ATTACHMENT_SIZE:
                errors.append(self.env._(
                    "Attachment exceeds the maximum file size of 1MB for SG B2G e-invoices"
                    " (size: %(size)s bytes).",
                    size=len(att['raw']),
                ))

        return errors
