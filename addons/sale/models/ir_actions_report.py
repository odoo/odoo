from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_order_edi_report_map(self):
        return {
            **super()._get_order_edi_report_map(),
            "sale.report_saleorder_document": "sale.order",
            "sale.report_saleorder": "sale.order",
            "sale.report_saleorder_raw": "sale.order",
        }

    def _get_order_print_report_map(self):
        return {
            **super()._get_order_print_report_map(),
            "sale.report_saleorder": "sale.order",
        }
