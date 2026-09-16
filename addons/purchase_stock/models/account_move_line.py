from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_price_unit_val_dif_and_relevant_qty(self):
        _debug.logic("price_difference_inputs", lines=self)
        self.check_singleton()
        valuation_price_unit = self.product_id.uom_id._get_price_in_unit(
            self.product_id.standard_price,
            self.product_uom_id,
        )
        valuation_price_unit = (
            -valuation_price_unit
            if self.move_id.move_type == "in_refund"
            else valuation_price_unit
        )
        valuation_date = self.date
        valuation_price_unit = self.company_currency_id._convert(
            valuation_price_unit,
            self.currency_id,
            self.company_id,
            valuation_date,
            round=False,
        )
        price_unit = self._get_gross_unit_price()
        price_unit_val_dif = price_unit - valuation_price_unit
        relevant_qty = self.quantity
        return price_unit_val_dif, relevant_qty

    def _get_stock_moves(self):
        return super()._get_stock_moves() | self.purchase_line_ids.move_ids

    def _prepare_price_difference_vals(self, quantity, amount_currency, account):
        _debug.pipeline("price_difference_vals", lines=self, quantity=quantity)
        self.check_singleton()
        return {
            "name": self.name[:64],
            "move_id": self.move_id.id,
            "partner_id": self.partner_id.id or self.move_id.commercial_partner_id.id,
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "quantity": quantity,
            "balance": self.currency_id._convert(
                amount_currency,
                self.company_currency_id,
                self.company_id,
                fields.Date.today(),
            ),
            "account_id": account.id,
            "analytic_distribution": self.analytic_distribution,
            "display_type": "cogs",
            "tax_ids": [],
        }
