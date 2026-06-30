# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _purchase_service_prepare_line_values(self, purchase_order, quantity=False):
        purchase_line_vals = super()._purchase_service_prepare_line_values(purchase_order, quantity)
        analytic_distribution = self.order_id.project_id._get_analytic_distribution()
        if not self.analytic_distribution and analytic_distribution:
            purchase_line_vals['analytic_distribution'] = analytic_distribution
        return purchase_line_vals

    def _purchase_service_prepare_order_values(self, supplierinfo):
        return {
            **super()._purchase_service_prepare_order_values(supplierinfo),
            'project_id': self.order_id.project_id.id,
        }
