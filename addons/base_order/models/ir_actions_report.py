import io

from odoo import models
from odoo.libs.debug_log import DebugLog
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_debug = DebugLog(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_order_edi_report_map(self):
        return {}

    def _get_order_print_report_map(self):
        return {}

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        model_name = self._get_order_print_report_map().get(
            self._get_report(report_ref).report_name
        )
        order_ids, _data = self._normalize_render_args(res_ids, data, "pdf")
        if model_name and order_ids:
            _debug.lifecycle(
                "orders_marked_printed", model=model_name, orders=len(order_ids)
            )
            self.env[model_name].sudo().browse(order_ids)._mark_as_printed()
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        collected_streams = super()._render_qweb_pdf_prepare_streams(
            report_ref,
            data,
            res_ids=res_ids,
        )

        if not collected_streams or not res_ids or len(res_ids) != 1:
            return collected_streams

        report_map = self._get_order_edi_report_map()
        if not report_map:
            return collected_streams

        model_name = report_map.get(self._get_report(report_ref).report_name)
        if not model_name:
            return collected_streams

        order = self.env[model_name].browse(res_ids)
        builders = order._get_edi_builders()
        if not builders:
            _debug.logic("edi_embed_skipped", order=order, reason="no_builder")
            return collected_streams

        return self._embed_order_edi_documents(collected_streams, order, builders)

    def _embed_order_edi_documents(self, collected_streams, order, builders):
        stream_entry = collected_streams.get(order.id)
        if not stream_entry or not stream_entry.get("stream"):
            _debug.logic("edi_embed_skipped", order=order, reason="no_pdf_stream")
            return collected_streams
        pdf_stream = stream_entry["stream"]
        pdf_content = pdf_stream.getvalue()
        reader_buffer = io.BytesIO(pdf_content)
        reader = OdooPdfFileReader(reader_buffer, strict=False)
        writer = OdooPdfFileWriter()
        writer.clone_reader_document_root(reader)

        order_sudo = order.sudo()
        for builder in builders:
            xml_content = builder._export_order(order_sudo)

            writer.add_attachment(
                order._get_edi_filename(builder),
                xml_content,
                subtype="text/xml",
            )

        pdf_stream.close()
        new_pdf_stream = io.BytesIO()
        writer.write(new_pdf_stream)
        reader_buffer.close()
        collected_streams[order.id]["stream"] = new_pdf_stream
        _debug.pipeline(
            "edi_documents_embedded",
            order=order,
            builders=len(builders),
            bytes=len(pdf_content),
        )

        return collected_streams
