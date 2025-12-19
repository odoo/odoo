# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

from lxml import etree
import base64
from xml.sax.saxutils import escape, quoteattr
import io


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _is_invoice_report(self, report_ref):
        # EXTENDS account
        # allows to add factur-x.xml to custom PDF templates (comma separated list of template names)
        custom_templates = self.env['ir.config_parameter'].sudo().get_param('account.custom_templates_facturx_list', '')
        custom_templates = [report.strip() for report in custom_templates.split(',')]
        return super()._is_invoice_report(report_ref) or self._get_report(report_ref).report_name in custom_templates

    @api.model
    def _get_edi_document_format_codes_for_pdf_embedding(self):
        return ['ubl_bis3', 'ubl_de', 'nlcius_1', 'efff_1']

    def _add_pdf_into_invoice_xml(self, invoice, stream_data):
        format_codes = self._get_edi_document_format_codes_for_pdf_embedding()
        edi_attachments = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code in format_codes).sudo().attachment_id
        for edi_attachment in edi_attachments:
            self._add_attachments_into_invoice_xml(
                invoice,
                edi_attachment,
                [{
                    'name': '%s.pdf' % invoice.name.replace('/', '_'),
                    'raw_b64': base64.b64encode(stream_data['stream'].getvalue()).decode(),
                    'mimetype': 'application/pdf',
                }],
                is_main_pdf=True,
                check_for_additionnal_document_elements=True,
            )

    @api.model
    def _add_attachments_into_invoice_xml(self, invoice, xml_attachment, extra_attachments, is_main_pdf=False, check_for_additionnal_document_elements=False):
        """
        Helper to embed the extra attachments into the xml file
        :param invoice: The invoice it is all about
        :param xml_attachment: The xml file that will contain embedded attachments
        :param extra_attachments: A list of dicts like `[{'name': 'filename', 'raw_b64': 'b64 encoded file content', 'mimetype': 'file mimetype'}, ]`
        :param is_main_pdf: Is the extra attachments list containing ONLY the Invoice PDF
        :param check_for_additionnal_document_elements: flag to not embed extra attachments if any document is already embedded into the xml
        """
        # [{'name': '', 'raw_b64': '', 'mimetype': ''}, {'name': '', 'raw_b64': '', 'mimetype': ''}]
        old_xml = base64.b64decode(xml_attachment.with_context(bin_size=False).datas, validate=True)
        tree = etree.fromstring(old_xml)
        anchor_elements = tree.xpath("//*[local-name()='AccountingSupplierParty']")
        additional_document_elements = tree.xpath("//*[local-name()='AdditionalDocumentReference']")
        if check_for_additionnal_document_elements and anchor_elements and additional_document_elements:
            return
        anchor_index = tree.index(anchor_elements[0])
        is_main_pdf = is_main_pdf and len(extra_attachments) == 1
        xmlns_invoice = 'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"' if is_main_pdf else ''
        for attachment in extra_attachments:
            to_inject = '''
                <cac:AdditionalDocumentReference
                    %s
                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
                    <cbc:ID>%s</cbc:ID>
                    <cac:Attachment>
                        <cbc:EmbeddedDocumentBinaryObject mimeCode=%s filename=%s>
                            %s
                        </cbc:EmbeddedDocumentBinaryObject>
                    </cac:Attachment>
                </cac:AdditionalDocumentReference>
            ''' % (
                xmlns_invoice,
                escape(attachment['name']),
                quoteattr(attachment['mimetype']),
                quoteattr(attachment['name']),
                attachment['raw_b64'],
            )

            tree.insert(anchor_index, etree.fromstring(to_inject))

        new_xml = etree.tostring(cleanup_xml_node(tree), xml_declaration=True, encoding='UTF-8')
        fields_values = {
            'datas': base64.b64encode(new_xml),
            'mimetype': 'application/xml',
        }
        if is_main_pdf:
            fields_values['res_model'] = 'account.move'
            fields_values['res_id'] = invoice.id
        xml_attachment.sudo().write(fields_values)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        # Add the pdf report in the XML as base64 string.
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        if collected_streams \
                and res_ids \
                and self._is_invoice_report(report_ref):
            for res_id, stream_data in collected_streams.items():
                invoice = self.env['account.move'].browse(res_id)
                self._add_pdf_into_invoice_xml(invoice, stream_data)

            # If Factur-X isn't already generated, generate and embed it inside the PDF
            if len(res_ids) == 1:
                invoice = self.env['account.move'].browse(res_ids)
                edi_doc_codes = invoice.edi_document_ids.edi_format_id.mapped('code')
                # If Factur-X hasn't been generated, generate and embed it anyway
                if invoice.is_sale_document() \
                        and invoice.state == 'posted' \
                        and 'facturx_1_0_05' not in edi_doc_codes \
                        and self.env.ref('account_edi_ubl_cii.edi_facturx_1_0_05', raise_if_not_found=False):
                    # Add the attachments to the pdf file
                    pdf_stream = collected_streams[invoice.id]['stream']

                    # Read pdf content.
                    pdf_content = pdf_stream.getvalue()
                    reader_buffer = io.BytesIO(pdf_content)
                    reader = OdooPdfFileReader(reader_buffer, strict=False)

                    # Post-process and embed the additional files.
                    writer = OdooPdfFileWriter()
                    writer.cloneReaderDocumentRoot(reader)

                    # Generate and embed Factur-X
                    xml_content, _errors = self.env['account.edi.xml.cii']._export_invoice(invoice)
                    writer.addAttachment(
                        name=self.env['account.edi.xml.cii']._export_invoice_filename(invoice),
                        data=xml_content,
                        subtype='text/xml',
                    )

                    # Replace the current content.
                    pdf_stream.close()
                    new_pdf_stream = io.BytesIO()
                    writer.write(new_pdf_stream)
                    collected_streams[invoice.id]['stream'] = new_pdf_stream

        return collected_streams
