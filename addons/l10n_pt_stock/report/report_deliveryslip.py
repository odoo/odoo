from odoo import api, models


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _name = 'report.stock.report_deliveryslip'
    _description = 'Stock delivery slip report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.company.account_fiscal_country_id.code == 'PT':
            self.env['stock.picking']._l10n_pt_compute_missing_hashes(self.env.company)
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'data': data,
            'docs': self.env['stock.picking'].browse(docids),
        }
