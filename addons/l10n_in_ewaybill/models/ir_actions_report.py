from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_ewaybills_to_print(self, report_ref, res_ids, data):
        if (
            self._get_report(report_ref).report_name
            != "l10n_in_ewaybill.report_ewaybill"
        ):
            return self.env["l10n.in.ewaybill"]
        ewaybill_ids, _data = self._normalize_render_args(res_ids, data, "pdf")
        return self.env["l10n.in.ewaybill"].browse(ewaybill_ids)

    def _pre_render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        self._get_ewaybills_to_print(report_ref, res_ids, data)._check_printable()
        return super()._pre_render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        content, report_type = super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )
        ewaybills = self._get_ewaybills_to_print(report_ref, res_ids, data)
        if report_type == "pdf" and len(ewaybills) == 1:
            ewaybills._add_printed_pdf_attachment(content)
        return content, report_type
