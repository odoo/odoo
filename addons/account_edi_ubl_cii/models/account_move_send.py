import base64
import logging
import io

from lxml import etree

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

        peppol_formats = set(self.env['res.partner']._get_peppol_formats())
        if peppol_format_moves := moves.filtered(lambda m: moves_data[m]['invoice_edi_format'] in peppol_formats):
            not_configured_company_partners = peppol_format_moves.company_id.partner_id.filtered(
                lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
            )
            if not_configured_company_partners:
                alerts['account_edi_ubl_cii_configure_company'] = {
                    'message': _("Please fill in your company's VAT or Peppol Address to generate a complete XML file."),
                    'level': 'info',
                    'action_text': _("Configure"),
                    'action': not_configured_company_partners._get_records_action(),
                }
            not_configured_partners = peppol_format_moves.partner_id.commercial_partner_id.filtered(
                lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
            )
            if not_configured_partners:
                alerts['account_edi_ubl_cii_configure_partner'] = {
                    'message': _("Please fill in partner's VAT or Peppol Address."),
                    'level': 'info',
                    'action_text': _("View Partner(s)"),
                    'action': not_configured_partners._get_records_action(name=_("Check Partner(s)"))
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
            self.env['ir.attachment'].sudo().create({
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
    def _get_attachments_widget(self, invoice, invoice_data):
        if 'email' in invoice_data['sending_methods']:
            return invoice_data.get('mail_attachments_widget', [])
        return []

    @api.model
    def _get_extra_additional_document_references(self, invoice, invoice_data):
        doc_refs = []
        for attachment_data in self._get_attachments_widget(invoice, invoice_data):
            if attachment_data.get('can_be_xml_embedded'):
                try:
                    attachment_id = int(attachment_data.get('id'))
                except ValueError:
                    continue

                if attachment := self.env['ir.attachment'].browse(attachment_id).exists():
                    doc_refs.append({
                        'id': attachment.name,  # this is not ideal, but we don't have any better option
                        'document_description': attachment.description or attachment.name,
                        'attachment_vals': {
                            'embedded_document_binary_object_attrs': {
                                'mimeCode': attachment.mimetype,
                                'filename': attachment.store_fname,
                            },
                            'embedded_document_binary_object': attachment.datas,
                        },
                    })
        return doc_refs

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        # Adding additional document references (and in particular the PDF of the invoice).
        tree = etree.fromstring(invoice_data['ubl_cii_xml_attachment_values']['raw'])
        # <AdditionalDocumentReference> is directly after optional <Signature> node.
        # <AccountingSupplierParty> is the first required node therefore used as fallback.
        anchor_elements = tree.xpath("//*[local-name()='Signature'] | //*[local-name()='AccountingSupplierParty']")
        if not anchor_elements:
            return
        anchor_index = tree.index(anchor_elements[0])

        pdf_values = invoice.invoice_pdf_report_id or invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']
        filename = pdf_values['name']
        content = pdf_values['raw']

        edi_model = invoice_data["ubl_cii_xml_options"]["builder"]
        doc_type_code_vals = edi_model._get_document_type_code_vals(invoice, invoice_data)
        additional_document_reference_list = [
            {
                'id': filename,
                'document_type_code_attrs': doc_type_code_vals['attrs'],
                'document_type_code': doc_type_code_vals['value'],
                'attachment_vals': {
                    'embedded_document_binary_object_attrs': {
                        'mimeCode': 'application/pdf',
                        'filename': filename,
                    },
                    'embedded_document_binary_object': base64.b64encode(content).decode(),
                },
            },
        ]
        additional_document_reference_list += self._get_extra_additional_document_references(invoice, invoice_data)
        doc_ref_template = 'ubl_20_DocumentReferenceType' if edi_model._name == 'account.edi.xml.oioubl' else 'ubl_21_DocumentReferenceType'
        to_inject = self.env['ir.qweb']._render('account_edi_ubl_cii.ubl_20_AdditionalDocumentReferences', {
            'DocumentReferenceType_template': f'account_edi_ubl_cii.{doc_ref_template}',
            'vals': additional_document_reference_list,
        })
        wrapped_to_inject = cleanup_xml_node(f'<wrapper>{to_inject}</wrapper>')
        for i, element_to_inject in enumerate(wrapped_to_inject):
            tree.insert(anchor_index + i, element_to_inject)
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
