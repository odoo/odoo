# Copyright 2015 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, exceptions, fields, models
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)


class ReportAction(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("xlsx", "XLSX")], ondelete={"xlsx": "set default"}
    )

    @api.model
    def _render_xlsx(self, report_ref, docids, data):
        report_sudo = self._get_report(report_ref)
        report_model_name = "report.%s" % report_sudo.report_name
        report_model = self.env[report_model_name]
        ret = (
            report_model.with_context(active_model=report_sudo.model)
            .sudo(False)
            .create_xlsx_report(docids, data)  # noqa
        )
        if ret and isinstance(ret, (tuple, list)):  # data, "xlsx"
            report_sudo.save_xlsx_report_attachment(docids, ret[0])
        return ret

    @api.model
    def _get_report_from_name(self, report_name):
        res = super()._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env["ir.actions.report"]
        qwebtypes = ["xlsx"]
        conditions = [
            ("report_type", "in", qwebtypes),
            ("report_name", "=", report_name),
        ]
        context = self.env["res.users"].context_get()
        return report_obj.with_context(**context).search(conditions, limit=1)

    def save_xlsx_report_attachment(self, docids, report_contents):
        """Save as attachment when the report is set up as such."""
        # Similar to ir.actions.report::_render_qweb_pdf in the base module.
        if not self.attachment:
            return
        if len(docids) != 1:  # unlike PDFs, here we don't have multiple streams
            _logger.warning(f"{self.name}: No records to save attachments onto.")
            return
        record = self.env[self.model].browse(docids)
        attachment_name = safe_eval(self.attachment, {"object": record, "time": time})
        if not attachment_name:
            return  # same as for PDFs, get out silently when name fails
        attachment_values = {
            "name": attachment_name,
            "raw": report_contents,
            "res_id": record.id,
            "res_model": self.model,
            "type": "binary",
        }
        try:
            attachment = self.env["ir.attachment"].create(attachment_values)
        except exceptions.AccessError:
            _logger.info(
                "Cannot save XLSX report %r attachment for user %r",
                attachment_values["name"],
                self.env.user.display_name,
            )
        else:
            _logger.info(
                "The XLSX document %r is now saved in the database",
                attachment_values["name"],
            )
        return attachment, record
