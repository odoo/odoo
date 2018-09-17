# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

from PyPDF2 import PdfFileWriter, PdfFileReader

import io


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.multi
    def _post_pdf(self, save_in_attachment, pdf_content=None, res_ids=None):
        # OVERRIDE
        if self.model == 'account.invoice' and res_ids and len(res_ids) == 1:
            invoice = self.env['account.invoice'].browse(res_ids)
            if invoice.type in ('out_invoice', 'out_refund') and invoice.state != 'draft':
                xml_content = invoice._export_as_facturx_xml()

                # Add attachment.
                reader_buffer = io.BytesIO(pdf_content)
                reader = PdfFileReader(reader_buffer)
                writer = PdfFileWriter()
                writer.cloneReaderDocumentRoot(reader)
                writer.addAttachment('factur-x.xml', xml_content)
                buffer = io.BytesIO()
                writer.write(buffer)
                pdf_content = buffer.getvalue()

                reader_buffer.close()
                buffer.close()
        return super(IrActionsReport, self)._post_pdf(save_in_attachment, pdf_content=pdf_content, res_ids=res_ids)
