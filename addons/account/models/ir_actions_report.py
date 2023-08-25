# -*- coding: utf-8 -*-
from collections import OrderedDict
from zlib import error as zlib_error
try:
    from PyPDF2.errors import PdfStreamError, PdfReadError
except ImportError:
    from PyPDF2.utils import PdfStreamError, PdfReadError

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools import pdf


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # Custom behavior for 'account.report_original_vendor_bill'.
        if self._get_report(report_ref).report_name != 'account.report_original_vendor_bill':
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        invoices = self.env['account.move'].browse(res_ids)
        original_attachments = invoices.message_main_attachment_id
        if not original_attachments:
            raise UserError(_("No original purchase document could be found for any of the selected purchase documents."))

        collected_streams = OrderedDict()
        for invoice in invoices:
            attachment = invoice.message_main_attachment_id
            if attachment:
                stream = pdf.to_pdf_stream(attachment)
                if stream:
                    record = self.env[attachment.res_model].browse(attachment.res_id)
                    try:
                        stream = pdf.add_banner(stream, record.name, logo=True)
                    except (ValueError, PdfStreamError, PdfReadError, TypeError, zlib_error, NotImplementedError):
                        record._message_log(body=_(
                            "There was an error when trying to add the banner to the original PDF.\n"
                            "Please make sure the source file is valid."
                        ))
                collected_streams[invoice.id] = {
                    'stream': stream,
                    'attachment': attachment,
                }
        return collected_streams

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Check for reports only available for invoices.
        # + append context data with the display_name_in_footer parameter
        if self._get_report(report_ref).report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            invoices = self.env['account.move'].browse(res_ids)
            if self.env['ir.config_parameter'].sudo().get_param('account.display_name_in_footer'):
                data = data and dict(data) or {}
                data.update({'display_name_in_footer': True})
            if any(x.move_type == 'entry' for x in invoices):
                raise UserError(_("Only invoices could be printed."))

        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
