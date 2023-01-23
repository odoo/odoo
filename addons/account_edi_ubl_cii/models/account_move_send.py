# -*- coding: utf-8 -*-
import base64
import io
import logging

from lxml import etree
from xml.sax.saxutils import escape, quoteattr

from odoo import _, api, fields, models, tools, Command
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    enable_ubl_cii_xml = fields.Boolean(compute='_compute_send_mail_extra_fields')
    ubl_cii_xml = fields.Boolean(
        string="UBL/CII EDI",
        compute='_compute_ubl_cii_xml',
        store=True,
        readonly=False,
    )

    def _compute_send_mail_extra_fields(self):
        # EXTENDS 'account'
        super()._compute_send_mail_extra_fields()
        for wizard in self:
            wizard.enable_ubl_cii_xml = \
                wizard.mode in ('invoice_single', 'invoice_multi') \
                and any(x._get_ubl_cii_builder() and not x.pdf_report_id for x in wizard.move_ids)

    @api.model
    def _get_default_mail_attachments_data(self, mail_template, move):
        # EXTENDS 'account'
        results = super()._get_default_mail_attachments_data(mail_template, move)

        if move.pdf_report_id and move.ubl_cii_xml_id:
            attachment = move.ubl_cii_xml_id
            results.append({
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
            })

        return results

    @api.depends('enable_ubl_cii_xml')
    def _compute_ubl_cii_xml(self):
        for wizard in self:
            # TODO: field on company?
            wizard.ubl_cii_xml = True

    def _get_invoice_ubl_cii_builder(self, invoice):
        self.ensure_one()

        # Prepare the xml.
        if self.enable_ubl_cii_xml:
            builder, options = invoice._get_ubl_cii_builder()
        else:
            builder, options = self.env['account.edi.xml.cii'], {'embed_to_pdf': True}
            options['skip_errors'] = True
        return builder, options

    def _prepare_invoice_documents(self, invoice):
        # EXTENDS 'account'
        ubl_cii_xml = self.enable_ubl_cii_xml and self.ubl_cii_xml

        if ubl_cii_xml:
            builder, options = self._get_invoice_ubl_cii_builder(invoice)
            xml_content, errors = builder._export_invoice(invoice)
            filename = builder._export_invoice_filename(invoice)

            # Failed.
            if errors and not options.get('skip_errors'):
                return {
                    'error': "".join([
                        _("Errors occur while creating the EDI document (format: %s):", builder._description),
                        "\n",
                        "<p><li>",
                        "</li><li>".join(errors),
                        "</li></p>",
                    ]),
                }

        # The xml is generated and checked first before the super call to avoid a not necessary PDF creation by
        # wkhtmltopdf.
        results = super()._prepare_invoice_documents(invoice)

        if ubl_cii_xml:
            results['ubl_cii_xml_attachment_values'] = {
                'name': filename,
                'raw': xml_content,
                'mimetype': 'application/xml',
                'res_model': invoice._name,
                'res_id': invoice.id,
            }

        return results

    def _postprocess_invoice_pdf(self, invoice, options, prepared_data):
        xml_attachment_values = prepared_data['ubl_cii_xml_attachment_values']

        # Read pdf content.
        reader_buffer = io.BytesIO(prepared_data['pdf_attachment_values']['raw'])
        reader = OdooPdfFileReader(reader_buffer, strict=False)

        # Post-process and embed the additional files.
        writer = OdooPdfFileWriter()
        writer.cloneReaderDocumentRoot(reader)
        writer.addAttachment(xml_attachment_values['name'], xml_attachment_values['raw'], subtype='text/xml')

        # PDF-A.
        if options.get('facturx_pdfa') and not writer.is_pdfa:
            try:
                writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)

            # Extra metadata to be Factur-x PDF-A compliant.
            content = self.env['ir.qweb']._render(
                'account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata',
                {
                    'title': invoice.name,
                    'date': fields.Date.context_today(self),
                },
            )
            writer.add_file_metadata(content.encode())

        # Replace the current content.
        writer_buffer = io.BytesIO()
        writer.write(writer_buffer)
        prepared_data['pdf_attachment_values']['raw'] = writer_buffer.getvalue()
        reader_buffer.close()
        writer_buffer.close()

    def _postprocess_invoice_ubl_cii_xml(self, invoice, options, prepared_data):
        if not options.get('ubl_inject_pdf'):
            return

        tree = etree.fromstring(prepared_data['ubl_cii_xml_attachment_values']['raw'])
        anchor_elements = tree.xpath("//*[local-name()='AccountingSupplierParty']")
        if not anchor_elements:
            return

        filename = prepared_data['pdf_attachment_values']['name']
        content = prepared_data['pdf_attachment_values']['raw']
        to_inject = f'''
            <cac:AdditionalDocumentReference
                xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
                <cbc:ID>{escape(filename)}</cbc:ID>
                <cac:Attachment>
                    <cbc:EmbeddedDocumentBinaryObject
                        mimeCode="application/pdf"
                        filename={quoteattr(filename)}>
                        {base64.b64encode(content).decode()}
                    </cbc:EmbeddedDocumentBinaryObject>
                </cac:Attachment>
            </cac:AdditionalDocumentReference>
        '''

        anchor_index = tree.index(anchor_elements[0])
        tree.insert(anchor_index, etree.fromstring(to_inject))
        prepared_data['ubl_cii_xml_attachment_values']['raw'] = etree.tostring(cleanup_xml_node(tree))

    def _generate_invoice_documents(self, invoice, prepared_data):
        # EXTENDS 'account'
        ubl_cii_xml = prepared_data.get('ubl_cii_xml_attachment_values')

        # Clear the previous xml.
        if invoice.ubl_cii_xml_id:
            invoice.ubl_cii_xml_id.unlink()

        if ubl_cii_xml:
            builder, options = self._get_invoice_ubl_cii_builder(invoice)

            # Create XML not embedded to the PDF.
            self._postprocess_invoice_pdf(invoice, options, prepared_data)
            self._postprocess_invoice_ubl_cii_xml(invoice, options, prepared_data)

        super()._generate_invoice_documents(invoice, prepared_data)

        # Create XML not embedded to the PDF.
        if ubl_cii_xml and not options.get('embed_to_pdf'):
            invoice.ubl_cii_xml_id = self.env['ir.attachment'].create(prepared_data['ubl_cii_xml_attachment_values'])

            self.mail_attachments_widget = (self.mail_attachments_widget or []) + [{
                'id': invoice.ubl_cii_xml_id.id,
                'name': invoice.ubl_cii_xml_id.name,
                'mimetype': invoice.ubl_cii_xml_id.mimetype,
            }]
