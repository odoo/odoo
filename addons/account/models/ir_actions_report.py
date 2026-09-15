from collections import OrderedDict
from itertools import groupby
from zlib import error as zlib_error

import lxml.html

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import pdf

_debug = DebugLog(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    is_invoice_report = fields.Boolean(
        string="Invoice report",
        copy=True,
    )

    @_debug.perf.timed
    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if (
            self._get_report(report_ref).report_name
            != "account.report_original_vendor_bill"
        ):
            return super()._render_qweb_pdf_prepare_streams(
                report_ref, data, res_ids=res_ids
            )

        invoices = self.env["account.move"].browse(res_ids)
        original_attachments = invoices.message_main_attachment_id
        _debug.logic(
            "original_vendor_bill_attachments",
            moves=invoices,
            attachments=original_attachments,
            missing_all=not original_attachments,
        )
        if not original_attachments:
            raise UserError(
                _(
                    "No original purchase document could be found for any of the selected purchase documents."
                )
            )

        collected_streams = OrderedDict()
        for invoice in invoices:
            attachment = self._migrate_attachments_to_local(
                invoice.message_main_attachment_id.sudo()
            )
            if attachment:
                stream = pdf.to_pdf_stream(attachment)
                if stream and attachment.res_model:
                    record = self.env[attachment.res_model].browse(attachment.res_id)
                    try:
                        stream = pdf.add_banner(stream, record.name or "", logo=True)
                    except (
                        ValueError,
                        pdf.PdfReadError,
                        TypeError,
                        zlib_error,
                        NotImplementedError,
                        pdf.DependencyError,
                        ArithmeticError,
                    ):
                        record._message_log(
                            body=_(
                                "There was an error when trying to add the banner to the original PDF.\n"
                                "Please make sure the source file is valid."
                            )
                        )
                collected_streams[invoice.id] = {
                    "stream": stream,
                    "attachment": attachment,
                }
        _debug.pipeline(
            "original_vendor_bill_streams",
            moves=invoices,
            streams=len(collected_streams),
        )
        return collected_streams

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        render = super()._render_qweb_pdf
        move_ids, _data = self._normalize_render_args(res_ids, data, "pdf")
        report = self._get_report(report_ref)
        invoice_report = self.env.ref("account.account_invoices", False)
        if not move_ids or report != invoice_report:
            return render(report_ref, res_ids=res_ids, data=data)
        if not self._is_pdf_rendering_enabled():
            return render(report_ref, res_ids=res_ids, data=data)

        send = self.env["mixin.account.move.send"]
        runs = [
            (template, [move.id for move in moves])
            for template, moves in groupby(
                self.env["account.move"].browse(move_ids),
                key=send._get_default_pdf_report_id,
            )
        ]
        if [template for template, _ids in runs] == [report]:
            return render(report_ref, res_ids=res_ids, data=data)
        documents = [render(template, ids, data=data)[0] for template, ids in runs]
        if len(documents) == 1:
            return documents[0], "pdf"
        return pdf.merge_pdf(documents), "pdf"

    def _is_invoice_report(self, report_ref):
        report = self._get_report(report_ref)
        return (
            report.is_invoice_report and report.model == "account.move"
        ) or report.report_name == "account.report_invoice"

    @_debug.perf.timed
    def _get_splitted_report(self, report_ref, content, report_type):
        if report_type == "html":
            report = self._get_report(report_ref)
            root = lxml.html.fromstring(
                content, parser=lxml.html.HTMLParser(encoding="utf-8")
            )
            articles = root.xpath(
                "//div[contains(concat(' ', normalize-space(@class), ' '), ' article ')]"
            )
            result = {}
            for article in articles:
                if article.get("data-oe-model") == report.model:
                    res_id = int(article.get("data-oe-id", 0))
                    result[res_id] = lxml.html.tostring(article)
            if not result and articles:
                for article in articles:
                    res_id = int(article.get("data-oe-id", 0))
                    if res_id:
                        result[res_id] = lxml.html.tostring(article)
            if not result:
                result[False] = (
                    content if isinstance(content, bytes) else content.encode()
                )
            _debug.logic(
                "html_report_split",
                report=report,
                articles=len(articles),
                parts=len(result),
                unsplit=False in result,
            )
            return result
        elif report_type == "pdf":
            pdf_dict = {
                res_id: stream["stream"].getvalue()
                for res_id, stream in content.items()
            }
            for stream in content.values():
                stream["stream"].close()
            _debug.pipeline(
                "pdf_report_split",
                parts=len(pdf_dict),
            )
            return pdf_dict

        return None

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if self._is_invoice_report(report_ref):
            invoices = self.env["account.move"].browse(res_ids)
            if (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("account.display_name_in_footer")
            ):
                data = (data and dict(data)) or {}
                data.update({"display_name_in_footer": True})
            if any(x.move_type == "entry" for x in invoices):
                raise UserError(_("Only invoices could be printed."))

        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    @api.ondelete(at_uninstall=False)
    @_debug.perf.timed
    def _unlink_except_master_tags(self):
        _debug.lifecycle("_unlink_except_master_tags", records=self)
        master_xmlids = [
            "account_invoices",
            "action_account_original_vendor_bill",
            "account_invoices_without_payment",
            "action_report_journal",
            "action_report_payment_receipt",
            "action_report_account_statement",
            "action_report_account_hash_integrity",
        ]
        for master_xmlid in master_xmlids:
            master_report = self.env.ref(
                f"account.{master_xmlid}", raise_if_not_found=False
            )
            if master_report and master_report in self:
                raise UserError(
                    _(
                        "You cannot delete this report (%s), it is used by the accounting PDF generation engine.",
                        master_report.name,
                    )
                )

    def _prepare_rendering_context(self, report, docids, data):
        data = super()._prepare_rendering_context(report, docids, data)
        if self.env.context.get("proforma_invoice"):
            data["proforma"] = True
        return data
