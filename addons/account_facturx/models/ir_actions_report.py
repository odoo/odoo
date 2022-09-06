# -*- coding: utf-8 -*-

import io

from odoo import models, fields
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.tools import str2bool

import logging

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        if collected_streams \
                and res_ids \
                and len(res_ids) == 1 \
                and self._get_report(report_ref).report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            invoice = self.env['account.move'].browse(res_ids)
            if invoice.is_sale_document() and invoice.state != 'draft':
                # Add the attachments to the pdf file
                pdf_stream = collected_streams[invoice.id]['stream']

                # Read pdf content.
                pdf_content = pdf_stream.getvalue()
                reader_buffer = io.BytesIO(pdf_content)
                reader = OdooPdfFileReader(reader_buffer, strict=False)

                # Post-process and embed the additional files.
                writer = OdooPdfFileWriter()
                writer.cloneReaderDocumentRoot(reader)
                self._prepare_invoice_report_facturx(writer, invoice)

                # Replace the current content.
                pdf_stream.close()
                new_pdf_stream = io.BytesIO()
                writer.write(new_pdf_stream)
                collected_streams[invoice.id]['stream'] = new_pdf_stream

        return collected_streams

    def _prepare_invoice_report_facturx(self, pdf_writer, invoice):
        facturx_content, errors = self.env['account.facturx']._export_invoice(invoice)
        # Don't want the Factur-X xml to appear in the attachments
        attachment = self.env['ir.attachment'].create({
            'name': 'factur-x.xml',
            'raw': facturx_content,
            'mimetype': 'application/xml',
            'res_id': None,
            'res_model': None,
        })
        pdf_writer.embed_odoo_attachment(attachment, subtype='text/xml')
        if not pdf_writer.is_pdfa and str2bool(
                self.env['ir.config_parameter'].sudo().get_param('edi.use_pdfa', 'False')):
            try:
                pdf_writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)
            metadata_template = self.env.ref('account_facturx.account_invoice_pdfa_3_facturx_metadata',
                                             raise_if_not_found=False)
            if metadata_template:
                content = self.env['ir.qweb']._render('account_facturx.account_invoice_pdfa_3_facturx_metadata', {
                    'title': 'factur-x.xml',
                    'date': fields.Date.context_today(self),
                })
                pdf_writer.add_file_metadata(content.encode())
