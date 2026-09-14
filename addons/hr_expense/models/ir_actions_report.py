import io

from odoo import models
from odoo.libs.debug_log import DebugLog
from odoo.tools import pdf
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

_debug = DebugLog(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        res = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids)
        if not res_ids:
            return res
        report = self._get_report(report_ref)
        if report.report_name == "hr_expense.report_expense":
            attachments_by_res_id = (
                self.env["ir.attachment"]
                .search([("res_id", "in", res_ids), ("res_model", "=", "hr.expense")])
                .grouped("res_id")
            )
            _debug.pipeline(
                "expense_report_streams",
                expenses=len(res_ids),
                with_attachments=len(attachments_by_res_id),
            )
            for expense in self.env["hr.expense"].browse(res_ids):
                stream_list = []
                stream = res[expense.id]["stream"]
                stream_list.append(stream)
                attachments = attachments_by_res_id.get(
                    expense.id, self.env["ir.attachment"]
                )
                expense_report = OdooPdfFileReader(stream, strict=False)
                output_pdf = OdooPdfFileWriter()
                output_pdf.append_pages_from_reader(expense_report)
                for attachment in self._migrate_attachments_to_local(attachments):
                    if attachment.mimetype == "application/pdf":
                        attachment_stream = pdf.to_pdf_stream(attachment)
                    else:
                        data["attachment"] = attachment
                        attachment_prep_stream = self._render_qweb_pdf_prepare_streams(
                            "hr_expense.report_expense_img", data, res_ids=res_ids
                        )
                        attachment_stream = attachment_prep_stream[expense.id]["stream"]
                    attachment_reader = OdooPdfFileReader(
                        attachment_stream, strict=False
                    )
                    output_pdf.append_pages_from_reader(attachment_reader)
                    stream_list.append(attachment_stream)

                new_pdf_stream = io.BytesIO()
                output_pdf.write(new_pdf_stream)
                _debug.perf.count(
                    "expense_report_merged", expense=expense, streams=len(stream_list)
                )
                res[expense.id]["stream"] = new_pdf_stream

                for stream in stream_list:
                    stream.close()
        return res
