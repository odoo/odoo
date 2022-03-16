# -*- coding: utf-8 -*-

import io

from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, data, res_ids=None):
        # EXTENDS base
        collected_streams = super()._render_qweb_pdf_prepare_streams(data, res_ids=res_ids)

        if collected_streams and res_ids and len(res_ids) == 1:
            record = self.env[self.model].browse(res_ids)
            if 'edi.document.mixin' in record._inherit:
                # Get all edi flows that are in send mode and needs embedding for this document.
                flows = record.edi_flow_ids.filtered(lambda f: (
                        f.flow_type == 'send'
                        and f._get_edi_format_settings().get('document_needs_embedding')
                    # todo also check self.report_name in ('account.report_invoice_with_payments', 'account.report_invoice') (? Filter on the report name? After latest changes, to see
                ))
                # Add the attachments to the pdf file
                if flows:
                    to_embed = flows.edi_file_ids.attachment_id
                    if to_embed:
                        pdf_stream = collected_streams[record.id]['stream']

                        # Read pdf content.
                        pdf_content = pdf_stream.getvalue()
                        reader_buffer = io.BytesIO(pdf_content)
                        reader = OdooPdfFileReader(reader_buffer, strict=False)

                        # Post-process and embed the additional files.
                        writer = OdooPdfFileWriter()
                        writer.cloneReaderDocumentRoot(reader)
                        for edi_flow in flows:
                            edi_flow.edi_format_id._prepare_document_report(writer, edi_flow.edi_file_ids)

                        # Replace the current content.
                        pdf_stream.close()
                        new_pdf_stream = io.BytesIO()
                        writer.write(new_pdf_stream)
                        collected_streams[record.id]['stream'] = new_pdf_stream

        return collected_streams
