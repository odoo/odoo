# -*- coding: utf-8 -*-
import base64
import logging
import io

from lxml import etree
from xml.sax.saxutils import escape, quoteattr

from odoo import _, api, fields, models, tools
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    enable_ubl_cii_xml = fields.Boolean(compute='_compute_send_mail_extra_fields')
    checkbox_ubl_cii_label = fields.Char(compute='_compute_checkbox_ubl_cii_label')  # label for the checkbox_ubl_cii_xml field
    checkbox_ubl_cii_xml = fields.Boolean(compute='_compute_checkbox_ubl_cii_xml', store=True, readonly=False)

    @api.model
    def _get_default_enable_ubl_cii_xml(self, move):
        return not move.invoice_pdf_report_id and move.is_sale_document() and move.partner_id.ubl_cii_format

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_checkbox_ubl_cii_label(self):
        for wizard in self:
            code_to_label = dict(wizard.move_ids.partner_id._fields['ubl_cii_format'].selection)
            codes = wizard.move_ids.partner_id.mapped('ubl_cii_format')
            if any(codes):
                wizard.checkbox_ubl_cii_label = ", ".join(code_to_label[c] for c in codes)
            else:
                wizard.checkbox_ubl_cii_label = False

    def _compute_send_mail_extra_fields(self):
        # EXTENDS 'account'
        super()._compute_send_mail_extra_fields()
        for wizard in self:
            wizard.enable_ubl_cii_xml = any(self._get_default_enable_ubl_cii_xml(m) for m in wizard.move_ids)

    @api.depends('checkbox_ubl_cii_xml')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('enable_ubl_cii_xml')
    def _compute_checkbox_ubl_cii_xml(self):
        for wizard in self:
            wizard.checkbox_ubl_cii_xml = True

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_linked_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_linked_attachments(move) + move.ubl_cii_xml_id

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if self.enable_ubl_cii_xml and self.checkbox_ubl_cii_xml:
            builder = move.partner_id._get_edi_builder()
            filename = builder._export_invoice_filename(move)
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _prepare_document(self, invoice):
        # EXTENDS 'account'
        results = super()._prepare_document(invoice)

        if self.checkbox_ubl_cii_xml and self._get_default_enable_ubl_cii_xml(invoice):
            builder = invoice.partner_id._get_edi_builder()

            xml_content, errors = builder._export_invoice(invoice)
            filename = builder._export_invoice_filename(invoice)

            # Failed.
            if errors:
                return {
                    'error': "".join([
                        _("Errors occured while creating the EDI document (format: %s):", builder._description),
                        "\n",
                        "<p><li>" + "</li><li>".join(errors) + "</li></p>" if self.mode == 'invoice_multi' \
                            else "\n".join(errors)
                    ]),
                }

            results['ubl_cii_xml_attachment_values'] = {
                'name': filename,
                'raw': xml_content,
                'mimetype': 'application/xml',
                'res_model': invoice._name,
                'res_id': invoice.id,
                'res_field': 'ubl_cii_xml_file',  # Binary field
            }
            results['ubl_cii_xml_options'] = {
                'ubl_cii_format': invoice.partner_id.ubl_cii_format,
                'builder': builder,
            }

        return results

    def _postprocess_document(self, invoice, prepared_data):
        # EXTENDS 'account'
        super()._postprocess_document(invoice, prepared_data)

        # Add PDF to XML
        if 'ubl_cii_xml_options' in prepared_data and prepared_data['ubl_cii_xml_options']['ubl_cii_format'] != 'facturx':
            self._postprocess_invoice_ubl_xml(invoice, prepared_data)

        # Always silently generate a Factur-X and embed it inside the PDF (inter-portability)
        if 'ubl_cii_xml_options' in prepared_data and prepared_data['ubl_cii_xml_options']['ubl_cii_format'] == 'facturx':
            xml_facturx = prepared_data['ubl_cii_xml_attachment_values']['raw']
        else:
            xml_facturx = self.env['account.edi.xml.cii']._export_invoice(invoice)[0]

        # during tests, no wkhtmltopdf, create the attachment for test purposes
        if tools.config['test_enable']:
            self.env['ir.attachment'].create({
                'name': 'factur-x.xml',
                'raw': xml_facturx,
                'res_id': invoice.id,
                'res_model': 'account.move',
            })
            return

        # Read pdf content.
        reader_buffer = io.BytesIO(prepared_data['pdf_attachment_values']['raw'])
        reader = OdooPdfFileReader(reader_buffer, strict=False)

        # Post-process.
        writer = OdooPdfFileWriter()
        writer.cloneReaderDocumentRoot(reader)

        writer.addAttachment('factur-x.xml', xml_facturx, subtype='text/xml')

        # PDF-A.
        if 'ubl_cii_xml_options' in prepared_data \
                and prepared_data['ubl_cii_xml_options']['ubl_cii_format'] == 'facturx' \
                and not writer.is_pdfa:
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

    def _postprocess_invoice_ubl_xml(self, invoice, prepared_data):
        # Add PDF to XML
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
        prepared_data['ubl_cii_xml_attachment_values']['raw'] = b"<?xml version='1.0' encoding='UTF-8'?>\n" \
            + etree.tostring(cleanup_xml_node(tree))

    def _link_document(self, invoice, prepared_data):
        # EXTENDS 'account'
        super()._link_document(invoice, prepared_data)

        attachment_vals = prepared_data.get('ubl_cii_xml_attachment_values')
        if attachment_vals:
            self.env['ir.attachment'].create(attachment_vals)
            invoice.invalidate_model(fnames=['ubl_cii_xml_id', 'ubl_cii_xml_file'])
