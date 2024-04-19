# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _l10n_in_compute_ewaybill_price_unit(self):
        self.ensure_one()
        return self.product_id.uom_id._compute_price(
            self.product_id.with_company(self.company_id).standard_price, self.product_uom
        )

    def _l10n_in_compute_line_tax(self):
        self.ensure_one()
        taxes = (
            self.picking_code == "incoming" and
            self.product_id.supplier_taxes_id or self.product_id.taxes_id
        )
        return self._get_l10n_in_fiscal_position(
            taxes.filtered_domain(self.env['account.tax']._check_company_domain(self.company_id))
        )
