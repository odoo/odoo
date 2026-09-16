from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _l10n_in_get_product_price_unit(self):
        self.check_singleton()
        return self.product_id.uom_id._get_price_in_unit(
            self.product_id.with_company(self.company_id).standard_price,
            self.product_uom_id,
        )

    def _l10n_in_get_product_tax(self):
        self.check_singleton()
        return {
            "is_from_order": False,
            "taxes": (
                (self.picking_code == "incoming" and self.product_id.supplier_taxes_id)
                or self.product_id.taxes_id
            ),
        }
