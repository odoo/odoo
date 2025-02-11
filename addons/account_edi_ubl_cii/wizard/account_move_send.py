# -*- coding: utf-8 -*-
import base64
import logging
import io

from lxml import etree
from xml.sax.saxutils import escape, quoteattr

from odoo import _, api, fields, models, tools, SUPERUSER_ID
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    enable_ubl_cii_xml = fields.Boolean(compute='_compute_enable_ubl_cii_xml')
    checkbox_ubl_cii_label = fields.Char(compute='_compute_checkbox_ubl_cii_label')
    checkbox_ubl_cii_xml = fields.Boolean(compute='_compute_checkbox_ubl_cii_xml', store=True, readonly=False)
    ubl_partner_warning = fields.Char(
        string="Partner warning",
        compute="_compute_ubl_warnings",
    )
    show_ubl_company_warning = fields.Boolean(
        string="Company warning",
        compute="_compute_ubl_warnings",
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['ubl_cii_xml'] = self.checkbox_ubl_cii_xml
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'checkbox_ubl_cii_xml': False,
            **values,
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_checkbox_ubl_cii_label(self):
        for wizard in self:
            wizard.checkbox_ubl_cii_label = False
            if wizard.mode in ('invoice_single', 'invoice_multi'):
                code_to_label = dict(wizard.move_ids.partner_id._fields['ubl_cii_format'].selection)
                codes = wizard.move_ids.partner_id.commercial_partner_id.mapped('ubl_cii_format')
                if any(codes):
                    wizard.checkbox_ubl_cii_label = ", ".join(code_to_label[c] for c in set(codes) if c)

    @api.depends('move_ids')
    def _compute_enable_ubl_cii_xml(self):
        for wizard in self:
            wizard.enable_ubl_cii_xml = any(m._need_ubl_cii_xml() for m in wizard.move_ids)

    @api.depends('checkbox_ubl_cii_xml')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('enable_ubl_cii_xml')
    def _compute_checkbox_ubl_cii_xml(self):
        for wizard in self:
            wizard.checkbox_ubl_cii_xml = wizard.enable_ubl_cii_xml and (wizard.checkbox_ubl_cii_xml or wizard.company_id.invoice_is_ubl_cii)

    @api.depends('move_ids')
    def _compute_ubl_warnings(self):
        for wizard in self:
            wizard.show_ubl_company_warning = False
            wizard.ubl_partner_warning = False
            if not set(wizard.move_ids.partner_id.commercial_partner_id.mapped('ubl_cii_format')) - {False, 'facturx', 'oioubl_201'}:
                return

            wizard.show_ubl_company_warning = not (wizard.company_id.partner_id.peppol_eas and wizard.company_id.partner_id.peppol_endpoint)
            not_configured_partners = wizard.move_ids.partner_id.commercial_partner_id.filtered(
                lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
            )
            if len(not_configured_partners) == 1:
                wizard.ubl_partner_warning = _("This partner is missing Peppol EAS or Peppol Endpoint field. "
                                        "Please check those in its Accounting tab or the generated file will be incomplete.")
            if len(not_configured_partners) > 1:
                names = ', '.join(not_configured_partners[:5].mapped('display_name'))
                wizard.ubl_partner_warning = _("The following partners are missing Peppol EAS or Peppol Endpoint field: %s. "
                                        "Please check those in their Accounting tab. "
                                        "Otherwise, the generated files will be incomplete.", names)

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.ubl_cii_xml_id

    def _needs_ubl_cii_placeholder(self):
        return self.enable_ubl_cii_xml and self.checkbox_ubl_cii_xml

    def _get_placeholder_mail_attachments_data(self, move):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move)

        if self.mode == 'invoice_single' and self._needs_ubl_cii_placeholder():
            builder = move.partner_id.commercial_partner_id._get_edi_builder()
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

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if invoice_data.get('ubl_cii_xml') and invoice._need_ubl_cii_xml():
            builder = invoice.partner_id.commercial_partner_id._get_edi_builder()
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
                    'ubl_cii_format': invoice.partner_id.commercial_partner_id.ubl_cii_format,
                    'builder': builder,
                }

    @api.model
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
        pdf_values = invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']
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
        pdf_values = invoice_data.get('pdf_attachment_values') or invoice_data['proforma_pdf_attachment_values']
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

    @api.model
    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)

        attachment_vals = invoice_data.get('ubl_cii_xml_attachment_values')
        if attachment_vals:
            self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_vals)
            invoice.invalidate_recordset(fnames=['ubl_cii_xml_id', 'ubl_cii_xml_file'])
