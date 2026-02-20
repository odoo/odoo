import base64
import logging
import io

from lxml import etree

from odoo import _, api, fields, models, tools, SUPERUSER_ID
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import SUPPORTED_FILE_TYPES
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.addons.account.tools import dict_to_xml

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_move_constraints(self, move):
        constraints = super()._get_move_constraints(move)
        if move._is_exportable_as_self_invoice():
            constraints.pop('not_sale_document', None)
        return constraints

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

            if any(
                    self.env['account.edi.xml.ubl_bis3']._is_customer_behind_chorus_pro(partner)
                    for partner in peppol_format_moves.partner_id.commercial_partner_id
                ):
                chorus_pro = self.env['ir.module.module'].sudo().search([('name', '=', 'l10n_fr_facturx_chorus_pro')], limit=1)
                if chorus_pro and chorus_pro.state != 'installed':
                    alerts['account_edi_ubl_cii_chorus_pro_install'] = {
                        'message': _("Please install the french Chorus pro module to have all the specific rules."),
                        'level': 'info',
                        'action': chorus_pro._get_records_action(),
                        'action_text': _("Install Chorus Pro"),
                    }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.ubl_cii_xml_id

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None, pdf_report=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis, pdf_report=pdf_report)
        if move._need_ubl_cii_xml(invoice_edi_format):
            builder = move.partner_id.commercial_partner_id._get_edi_builder(invoice_edi_format)
            filename = builder._export_invoice_filename(move)
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })
        return results

    @api.model
    def _display_attachments_widget(self, edi_format, sending_methods):
        ubl_format_info = self.env['res.partner']._get_ubl_cii_formats_info()
        return (
            super()._display_attachments_widget(edi_format, sending_methods)
            or ubl_format_info.get(edi_format, {}).get('embed_attachments')
        )

    @api.model
    def _get_ubl_available_attachments(self, mail_attachments_widget, invoice_edi_format):
        if not invoice_edi_format or not mail_attachments_widget:
            return self.env['ir.attachment'], self.env['ir.attachment']
        attachment_ids = [values['id'] for values in mail_attachments_widget if values.get('manual')]
        attachments = self.env['ir.attachment'].browse(attachment_ids)

        ubl_format_info = self.env['res.partner']._get_ubl_cii_formats_info().get(invoice_edi_format, {})
        if not ubl_format_info.get('embed_attachments'):
            return self.env['ir.attachment'], attachments

        accepted_attachments = attachments.filtered(lambda attachment: attachment.mimetype in SUPPORTED_FILE_TYPES)
        return accepted_attachments, attachments - accepted_attachments

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if invoice._need_ubl_cii_xml(invoice_data['invoice_edi_format']):
            builder = invoice.partner_id.commercial_partner_id._get_edi_builder(invoice_data['invoice_edi_format'])
            xml_content, errors = (
                builder
                .with_context(from_peppol='peppol' in invoice_data['sending_methods'])
                ._export_invoice(invoice)
            )
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
        if self._needs_ubl_postprocessing(invoice_data):
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
        pdf_values = (not self.env.context.get('custom_template_facturx') and invoice.invoice_pdf_report_id) or \
            invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']
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
            if "<pdfaid:conformance>B</pdfaid:conformance>" in content:
                content.replace("<pdfaid:conformance>B</pdfaid:conformance>", "<pdfaid:conformance>A</pdfaid:conformance>")
            writer.add_file_metadata(content.encode())

        # Replace the current content.
        writer_buffer = io.BytesIO()
        writer.write(writer_buffer)
        pdf_values['raw'] = writer_buffer.getvalue()
        reader_buffer.close()
        writer_buffer.close()

    @api.model
    def _needs_ubl_postprocessing(self, invoice_data):
        return 'ubl_cii_xml_options' in invoice_data and invoice_data['ubl_cii_xml_options']['ubl_cii_format'] != 'facturx'

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        """
        Include the PDF in the UBL as an AdditionalDocumentReference element.

        According to UBL 2.1 standard, the AdditionalDocumentReference element should be
        placed above ProjectReference which isn't usually in xml files.
        So usually it's set above AccountingSupplierParty. Here, we try to find a suitable anchor point among
        the available element to insert our PDF attachment. If none of these are found, we
        skip adding the attachment to avoid breaking the XML structure.
        Inside CreditNote, the ProjectReference element is not used in xml.
        So we look for OriginatorDocumentReference instead.
        """
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
        pdf_values = invoice.invoice_pdf_report_id or invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']

        edi_model = invoice_data["ubl_cii_xml_options"]["builder"]
        doc_type_code_node = edi_model._get_document_type_code_node(invoice, invoice_data)
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
                invoice_data['invoice_edi_format']
            )[0]
        ] if invoice_data.get('mail_attachments_widget') else []
        attachments_to_embed.append({
            'filename': pdf_values['name'],
            'raw': pdf_values['raw'],
            'mimetype': pdf_values['mimetype'],
            'document_type_node': doc_type_code_node,
        })

        for attachment_values in attachments_to_embed:
            additional_document_reference_node = {
                '_tag': 'cac:AdditionalDocumentReference',
                'cbc:ID': {'_text': attachment_values['filename']},
                'cbc:DocumentTypeCode': attachment_values.get('document_type_node'),
                'cac:Attachment': {
                    'cbc:EmbeddedDocumentBinaryObject': {
                        '_text': base64.b64encode(attachment_values['raw']).decode(),
                        'mimeCode': attachment_values['mimetype'],
                        'filename': attachment_values['filename']
                    }
                }
            }
            tree.insert(anchor_index, dict_to_xml(additional_document_reference_node, nsmap=nsmap))

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
