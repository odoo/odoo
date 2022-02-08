# -*- coding: utf-8 -*-

import io

from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # OVERRIDE to embed some EDI documents inside the PDF.
        if self.model == 'account.move' and res_ids and len(res_ids) == 1 and pdf_content:
            invoice = self.env['account.move'].browse(res_ids)
            if invoice.is_sale_document() and invoice.state != 'draft':
                to_embed = invoice.edi_document_ids
                # Add the attachments to the pdf file
                if to_embed:
                    reader_buffer = io.BytesIO(pdf_content)
                    reader = OdooPdfFileReader(reader_buffer, strict=False)
                    writer = OdooPdfFileWriter()
                    writer.cloneReaderDocumentRoot(reader)
                    for edi_document in to_embed:
                        edi_document.edi_format_id._prepare_invoice_report(writer, edi_document)
                    buffer = io.BytesIO()
                    writer.write(buffer)
                    pdf_content = buffer.getvalue()
                    reader_buffer.close()
                    buffer.close()

        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
