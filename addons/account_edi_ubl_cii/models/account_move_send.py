# -*- coding: utf-8 -*-
import io
import logging

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
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
            wizard.enable_ubl_cii_xml = wizard.mode in ('invoice_single', 'invoice_multi') \
                                        and any(x._get_ubl_cii_builder() for x in wizard.move_ids)

    @api.depends('enable_ubl_cii_xml')
    def _compute_ubl_cii_xml(self):
        for wizard in self:
            # TODO: field on company?
            wizard.ubl_cii_xml = True

    def _prepare_pdf_report(self, move):
        # EXTENDS 'account'
        self.ensure_one()

        # Prepare the xml.
        if self.enable_ubl_cii_xml:
            builder, options = move._get_ubl_cii_builder()
            odoo_default = False
        else:
            builder, options = self.env['account.edi.xml.cii'], {'embed_to_pdf': True}
            odoo_default = True

        xml_content, errors = builder._export_invoice(move)
        filename = builder._export_invoice_filename(move)

        if errors and not odoo_default:
            return {
                'pdf': False,
                'ubl_cii_xml_error': "".join([
                    _("Errors occured while creating the EDI document (format: %s):", builder._description),
                    "\n",
                    "<p><li>",
                    "</li><li>".join(errors),
                    "</li></p>",
                ]),
            }

        xml_attachment_values = {
            'name': filename,
            'raw': xml_content,
            'mimetype': 'application/xml',
        }

        # Prepare the PDF.
        prepared_data = super()._prepare_pdf_report(move)

        # Post-process the PDF.
        if options.get('embed_to_pdf') or options.get('pdfa'):
            # Read pdf content.
            reader_buffer = io.BytesIO(prepared_data['content'])
            reader = OdooPdfFileReader(reader_buffer, strict=False)

            # Post-process and embed the additional files.
            writer = OdooPdfFileWriter()
            writer.cloneReaderDocumentRoot(reader)
            if options.get('embed_to_pdf'):
                writer.addAttachment(xml_attachment_values['name'], xml_attachment_values['raw'], subtype='text/xml')

            # PDF-A.
            if options.get('pdfa') and not writer.is_pdfa:
                try:
                    writer.convert_to_pdfa()
                except Exception as e:
                    _logger.exception("Error while converting to PDF/A: %s", e)

                # Extra metadata to be Factur-x PDF-A compliant.
                content = self.env['ir.qweb']._render(
                    'account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata',
                    {
                        'title': move.name,
                        'date': fields.Date.context_today(self),
                    },
                )
                writer.add_file_metadata(content.encode())

            # Replace the current content.
            writer_buffer = io.BytesIO()
            writer.write(writer_buffer)
            prepared_data['content'] = writer_buffer.getvalue()
            reader_buffer.close()
            writer_buffer.close()

        # Post-process the XML.
        if not options.get('embed_to_pdf'):
            xml_attachment = self.env['ir.attachment'].create(xml_attachment_values)
            self.mail_attachments_widget = (self.mail_attachments_widget or []) + [{
                'id': xml_attachment.id,
                'name': xml_attachment.name,
                'mimetype': xml_attachment.mimetype,
            }]

        return prepared_data

    def _prepare_pdf_report_failed(self, move, prepared_data):
        # EXTENDS 'account'
        if prepared_data.get('ubl_cii_xml_error'):
            raise UserError(prepared_data['ubl_cii_xml_error'])
        else:
            super()._prepare_pdf_report_failed(move, prepared_data)
