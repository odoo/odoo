# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res["l10n_br_service_operation_indicator"] = self.l10n_br_service_operation_indicator
        return res
