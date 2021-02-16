from odoo import models



class PurchaseOrderReport(models.AbstractModel):
    _name = "report.qweb_report.report_purchase_a4_portrait"
    _description = "Purchase order report"

    def _get_report_values(self, docids, data=None):
        purchase = self.env['purchase.order'].browse(docids)

        return {
            'doc_ids': purchase.ids,
            'doc_model': 'purchase.order',
            'docs': purchase,
            'data': data,
        }