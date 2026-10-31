# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _update_summary_with_extra_cost_values(self, summary, production, quantity):
        super()._update_summary_with_extra_cost_values(summary, production, quantity)
        if production:
            last_done_receipt = production._get_last_done_receipt()
            summary['is_subcontract'] = bool(last_done_receipt.is_subcontract)
