# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class Report(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        if (
            self._get_report(report_ref).report_name
            == "mis_builder.report_mis_report_instance"
        ):
            if not res_ids:
                res_ids = self.env.context.get("active_ids")
            mis_report_instance = self.env["mis.report.instance"].browse(res_ids)[0]
            # data=None, because it was there only to force Odoo
            # to propagate context
            return super(
                Report, self.with_context(landscape=mis_report_instance.landscape_pdf)
            )._render_qweb_pdf(report_ref, res_ids, data=None)
        return super()._render_qweb_pdf(report_ref, res_ids, data)
