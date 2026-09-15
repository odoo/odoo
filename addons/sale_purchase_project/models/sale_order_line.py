from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _purchase_service_prepare_line_values(
        self, purchase_order, quantity=False, supplierinfo=None
    ):
        purchase_line_vals = super()._purchase_service_prepare_line_values(
            purchase_order, quantity, supplierinfo=supplierinfo
        )
        analytic_distribution = self.order_id.project_id._get_analytic_distribution()
        if not self.analytic_distribution and analytic_distribution:
            _debug.logic(
                "purchase_analytic_from_project",
                line=self,
                project=self.order_id.project_id,
            )
            purchase_line_vals["analytic_distribution"] = analytic_distribution
        return purchase_line_vals

    def _prepare_purchase_service_order_values(self, supplierinfo):
        return {
            **super()._prepare_purchase_service_order_values(supplierinfo),
            "project_id": self.order_id.project_id.id,
        }
