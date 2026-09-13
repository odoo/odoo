from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_order_edi_report_map(self):
        return {
            **super()._get_order_edi_report_map(),
            "purchase.report_purchasequotation": "purchase.order",
            "purchase.report_purchaseorder": "purchase.order",
        }

    def _get_order_print_report_map(self):
        return {
            **super()._get_order_print_report_map(),
            "purchase.report_purchasequotation": "purchase.order",
            "purchase.report_purchaseorder": "purchase.order",
        }
