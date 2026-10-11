from odoo import api, models


class ReportStockPickingDeliverySlip(models.AbstractModel):
    _name = 'report.stock.report_deliveryslip'
    _description = 'Stock delivery slip report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': self.env['stock.picking'],
            'data': data,
            'docs': self.env['stock.picking'].browse(docids),
        }
