# -*- coding: utf-8 -*-
import io
from collections import OrderedDict

from odoo import models, _
from odoo.tools import pdf
from odoo.exceptions import UserError
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _add_watermark_streams(self, streams, text):
        """ Add a watermark 'duplicated' to the PDF
        :param pdf_stream
        :return (BytesIO):  The modified PDF stream
        """
        for invoice_id, stream_dict in streams.items():
            input_pdf = PdfFileReader(stream_dict['stream'])

            packet = io.BytesIO()
            can = canvas.Canvas(packet)

            page = input_pdf.getPage(0)
            width = float(abs(page.mediaBox.getWidth()))
            height = float(abs(page.mediaBox.getHeight()))

            can.translate(width / 3.7, height / 1.4)

            # Set rotation angle
            can.rotate(-45)

            can.setFontSize(70)
            can.setFillAlpha(0.2)
            can.drawString(0, 0, text)

            # Save watermark pdf file
            can.save()

            # merge the two pages
            # Merge the old pages with the watermark
            watermark_pdf = PdfFileReader(packet, overwriteWarnings=False)
            new_pdf = PdfFileWriter()
            for p in range(input_pdf.getNumPages()):
                new_page = input_pdf.getPage(p)
                # Remove annotations (if any), to prevent errors in PyPDF2
                if '/Annots' in new_page:
                    del new_page['/Annots']
                new_page.mergePage(watermark_pdf.getPage(p))
                new_pdf.addPage(new_page)

            # Write the new pdf into a new output stream
            output = io.BytesIO()
            new_pdf.write(output)

            # debug
            with open("/home/odoo/Downloads/example-drafted.pdf", "wb") as output_file:
                new_pdf.write(output_file)

            new_stream = io.BytesIO()
            new_pdf.write(new_stream)
            stream_dict['stream'] = new_stream
        return streams

    def _render_qweb_pdf_prepare_streams(self, data, res_ids=None):
        # Add watermark
        # TODO: when do we want it to appear ? handle multiple invoices, handle original bills...
        if res_ids and self.report_name in ['account.report_invoice_with_payments', 'account.report_invoice']:
            old_streams = super()._render_qweb_pdf_prepare_streams(data, res_ids=res_ids)
            new_streams = self._add_watermark_streams(old_streams, _("DUPLICATED"))
            return new_streams

        # Custom behavior for 'account.report_original_vendor_bill'.
        if self.report_name != 'account.report_original_vendor_bill':
            return super()._render_qweb_pdf_prepare_streams(data, res_ids=res_ids)

        invoices = self.env['account.move'].browse(res_ids)
        if any(x.move_type not in ('in_invoice', 'in_receipt') for x in invoices):
            raise UserError(_("You can only print the original document for vendor bills."))

        original_attachments = invoices.message_main_attachment_id
        if not original_attachments:
            raise UserError(_("No original vendor bills could be found for any of the selected vendor bills."))

        collected_streams = OrderedDict()
        for invoice in invoices:
            attachment = invoice.message_main_attachment_id
            if attachment:
                stream = io.BytesIO(attachment.raw)
                if attachment.mimetype == 'application/pdf':
                    record = self.env[attachment.res_model].browse(attachment.res_id)
                    stream = pdf.add_banner(stream, record.name, logo=True)
                collected_streams[invoice.id] = {
                    'stream': stream,
                    'attachment': attachment,
                }
        return collected_streams

    def _render_qweb_pdf(self, res_ids=None, data=None):
        # Check for reports only available for invoices.
        if self.report_name in ('account.report_invoice_with_payments', 'account.report_invoice'):
            invoices = self.env['account.move'].browse(res_ids)
            if any(x.move_type == 'entry' for x in invoices):
                raise UserError(_("Only invoices could be printed."))

        return super()._render_qweb_pdf(res_ids=res_ids, data=data)
