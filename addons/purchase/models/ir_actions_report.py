import io

from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        # EXTENDS base
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

        if collected_streams \
                and res_ids \
                and len(res_ids) == 1 \
                and self._is_purchase_order_report(report_ref):
            purchase_order = self.env['purchase.order'].browse(res_ids)
            builders = purchase_order._get_edi_builders()

            if len(builders) == 0:
                return collected_streams

            # Read pdf content.
            pdf_stream = collected_streams[purchase_order.id]['stream']
            pdf_content = pdf_stream.getvalue()
            reader_buffer = io.BytesIO(pdf_content)
            reader = OdooPdfFileReader(reader_buffer, strict=False)
            writer = OdooPdfFileWriter()
            writer.cloneReaderDocumentRoot(reader)
            for builder in builders:
                xml_content = builder._export_order(purchase_order)

                # Post-process and embed the edi document.
                writer.addAttachment(
                    builder._export_purchase_order_filename(purchase_order),
                    xml_content,
                    subtype='text/xml'
                )

            # Replace the current content.
            pdf_stream.close()
            new_pdf_stream = io.BytesIO()
            writer.write(new_pdf_stream)
            collected_streams[purchase_order.id]['stream'] = new_pdf_stream

        return collected_streams

    def _is_purchase_order_report(self, report_ref):
        return self._get_report(report_ref).report_name in (
            'purchase.report_purchasequotation',
            'purchase.report_purchaseorder'
        )
