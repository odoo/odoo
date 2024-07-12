from odoo import api, models


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _inherit = 'report.stock.report_deliveryslip'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.company.account_fiscal_country_id.code == 'PT':
            self.env['stock.picking']._l10n_pt_stock_compute_missing_hashes(self.env.company.id)
        return super()._get_report_values(docids, data=data)
