from odoo import api, models


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _inherit = 'report.stock.report_deliveryslip'
    _description = 'Stock delivery slip report'

    @api.model
    def _get_report_values(self, docids, data=None):
        pickings = self.env['stock.picking'].browse(docids)
        # A PDF print signs the transfers in its checks (`ir.actions.report`), an HTML render does not:
        # the transfers still unsigned are signed here, in their own company, whichever is active.
        pickings.filtered(lambda p: p.country_code == 'PT')._l10n_pt_sign_unsigned()
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'data': data,
            'docs': pickings,
        }
