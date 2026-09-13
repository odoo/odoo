from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ReportAccountReport_Hash_Integrity(models.AbstractModel):
    _name = "report.account.report_hash_integrity"
    _description = "Get hash integrity result as PDF."

    @api.model
    @_debug.perf.timed
    def _get_report_values(self, docids, data=None):
        if data:
            data.update(self.env.company._check_hash_integrity())
        else:
            data = self.env.company._check_hash_integrity()
        return {
            "doc_ids": docids,
            "doc_model": self.env["res.company"],
            "data": data,
            "docs": self.env["res.company"].browse(self.env.company.id),
        }
