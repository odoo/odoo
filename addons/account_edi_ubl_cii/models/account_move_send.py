import base64
import logging
import io

from lxml import etree
from xml.sax.saxutils import escape, quoteattr

from odoo import _, api, fields, models, tools, SUPERUSER_ID
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if not set(moves.partner_id.commercial_partner_id.mapped('invoice_edi_format')) - {False, 'facturx', 'oioubl_201'}:
            return alerts

        ubl_formats = set(self.env['res.partner']._get_ubl_cii_formats())
        if ubl_moves := moves.filtered(lambda m: moves_data[m]['invoice_edi_format'] and moves_data[m]['invoice_edi_format'] in ubl_formats):
            not_configured_company_partners = ubl_moves.company_id.partner_id.filtered(
                lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
            )
            if not_configured_company_partners:
                alerts['account_edi_ubl_cii_configure_company'] = {
                    'message': _("Please fill in Peppol EAS and Peppol Endpoint in your company form to generate a complete file."),
                    'level': 'info',
                    'action_text': _("View Company"),
                    'action': not_configured_company_partners._get_records_action(),
                }
            not_configured_partners = ubl_moves.partner_id.commercial_partner_id.filtered(
                lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
            )
            if not_configured_partners:
                alerts['account_edi_ubl_cii_configure_partner'] = {
                    'message': _("These partners are missing Peppol EAS or Peppol Endpoint field. "
                                 "Please check those in their Accounting tab. "
                                 "Otherwise, the generated files will be incomplete."),
                    'level': 'info',
                    'action_text': _("View Partner(s)"),
                    'action': not_configured_partners._get_records_action(name=_("Check Partner(s)"))
                }
            moves_without_bank = ubl_moves.filtered(lambda m: not m.partner_bank_id)
            if moves_without_bank:
                alerts['account_edi_ubl_cii_configure_bank'] = {
                    'message': _("Please add a Recipient bank in the 'Other Info' tab to generate a complete file."),
                    'level': 'danger' if len(moves_without_bank) == 1 else 'warning',
                    'action_text': _("View Invoice(s)"),
                    'action': moves_without_bank._get_records_action(name=_("Check Invoice(s)")),
                }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.ubl_cii_xml_id

    def _get_placeholder_mail_attachments_data(self, move, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)
        partner_edi_format = self._get_default_invoice_edi_format(move)
        if move._need_ubl_cii_xml(partner_edi_format):
            builder = move.partner_id.commercial_partner_id._get_edi_builder(partner_edi_format)
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

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if invoice._need_ubl_cii_xml(invoice_data['invoice_edi_format']):
            builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
            xml_content, errors = builder._export_invoice(invoice)
            filename = builder._export_invoice_filename(invoice)

            # Failed.
            if errors:
                invoice_data['error'] = {
                    'error_title': _("Errors occurred while creating the EDI document (format: %s):", builder._description),
                    'errors': errors,
                }
                invoice_data['error_but_continue'] = True
            else:
                invoice_data['ubl_cii_xml_attachment_values'] = {
                    'name': filename,
                    'raw': xml_content,
                    'mimetype': 'application/xml',
                    'res_model': invoice._name,
                    'res_id': invoice.id,
                    'res_field': 'ubl_cii_xml_file',  # Binary field
                }
                invoice_data['ubl_cii_xml_options'] = {
                    'ubl_cii_format': invoice_data['invoice_edi_format'],
                    'builder': builder,
                }

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)

        # Add PDF to XML
        if 'ubl_cii_xml_options' in invoice_data and invoice_data['ubl_cii_xml_options']['ubl_cii_format'] != 'facturx':
            self._postprocess_invoice_ubl_xml(invoice, invoice_data)

        # Always silently generate a Factur-X and embed it inside the PDF for inter-portability
        if invoice_data.get('ubl_cii_xml_options', {}).get('ubl_cii_format') == 'facturx':
            xml_facturx = invoice_data['ubl_cii_xml_attachment_values']['raw']
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
        pdf_values = invoice.invoice_pdf_report_id or invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']
        reader_buffer = io.BytesIO(pdf_values['raw'])
        reader = OdooPdfFileReader(reader_buffer, strict=False)

        # Post-process.
        writer = OdooPdfFileWriter()
        writer.cloneReaderDocumentRoot(reader)

        writer.addAttachment('factur-x.xml', xml_facturx, subtype='text/xml')

        # PDF-A.
        if invoice_data.get('ubl_cii_xml_options', {}).get('ubl_cii_format') == 'facturx' \
                and not writer.is_pdfa:
            try:
                writer.convert_to_pdfa()
            except Exception:
                _logger.exception("Error while converting to PDF/A")

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
        pdf_values['raw'] = writer_buffer.getvalue()
        reader_buffer.close()
        writer_buffer.close()

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        # Adding the PDF to the XML
        tree = etree.fromstring(invoice_data['ubl_cii_xml_attachment_values']['raw'])
        anchor_elements = tree.xpath("//*[local-name()='AccountingSupplierParty']")
        if not anchor_elements:
            return

        xmlns_move_type = 'Invoice' if invoice.move_type == 'out_invoice' else 'CreditNote'
        pdf_values = invoice.invoice_pdf_report_id or invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']
        filename = pdf_values['name']
        content = pdf_values['raw']

        doc_type_node = ""
        edi_model = invoice_data["ubl_cii_xml_options"]["builder"]
        doc_type_code_vals = edi_model._get_document_type_code_vals(invoice, invoice_data)
        if doc_type_code_vals['value']:
            doc_type_code_attrs = " ".join(f'{name}="{value}"' for name, value in doc_type_code_vals['attrs'].items())
            doc_type_node = f"<cbc:DocumentTypeCode {doc_type_code_attrs}>{doc_type_code_vals['value']}</cbc:DocumentTypeCode>"
        to_inject = f'''
            <cac:AdditionalDocumentReference
                xmlns="urn:oasis:names:specification:ubl:schema:xsd:{xmlns_move_type}-2"
                xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
                <cbc:ID>{escape(filename)}</cbc:ID>
                {doc_type_node}
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
        invoice_data['ubl_cii_xml_attachment_values']['raw'] = etree.tostring(
            cleanup_xml_node(tree), xml_declaration=True, encoding='UTF-8'
        )

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        attachments_vals = [
            invoice_data.get('ubl_cii_xml_attachment_values')
            for invoice_data in invoices_data.values()
            if invoice_data.get('ubl_cii_xml_attachment_values')
        ]
        if attachments_vals:
            attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachments_vals)
            res_ids = attachments.mapped('res_id')
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['ubl_cii_xml_id', 'ubl_cii_xml_file'])
