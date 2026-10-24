from odoo import api, models


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _inherit = 'report.stock.report_deliveryslip'
    _description = 'Stock delivery slip report'

    @api.model
    def _get_report_values(self, docids, data=None):
        pickings = self.env['stock.picking'].browse(docids)
        # Signed in each transfer's own company, whichever company is active.
        if pt_pickings := pickings.filtered(lambda p: p.country_code == 'PT'):
            pt_pickings._l10n_pt_compute_missing_hashes()
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'data': data,
            'docs': pickings,
        }
