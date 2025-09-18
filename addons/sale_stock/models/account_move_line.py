from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _get_cogs_qty(self):
        self.ensure_one()
        valuation_account = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=self.move_id.fiscal_position_id
        )["stock_valuation"]
        posted_cogs_qty = sum(
            self.sale_line_ids.order_id.invoice_ids.filtered(
                lambda m: m.move_type == "out_invoice"
            )
            .line_ids.filtered(
                lambda line: line.product_id == self.product_id
                and line.display_type == "cogs"
                and line.account_id == valuation_account
            )
            .mapped("quantity")
        )
        return posted_cogs_qty + super()._get_cogs_qty()

    def _get_posted_cogs_value(self):
        self.ensure_one()
        valuation_account = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=self.move_id.fiscal_position_id
        )["stock_valuation"]
        posted_cogs_value = -sum(
            self.sale_line_ids.order_id.invoice_ids.filtered(
                lambda m: m.move_type == "out_invoice"
            )
            .line_ids.filtered(
                lambda line: line.product_id == self.product_id
                and line.display_type == "cogs"
                and line.account_id == valuation_account
            )
            .mapped("balance")
        )
        return posted_cogs_value + super()._get_posted_cogs_value()

    def _get_stock_moves(self):
        return super()._get_stock_moves() | self.sale_line_ids.move_ids

    # ------------------------------------------------------------
    # VAlIDATIONS
    # ------------------------------------------------------------

    def _sale_can_be_reinvoice(self):
        self.ensure_one()
        return (
            self.move_type != "entry"
            and self.display_type != "cogs"
            and super()._sale_can_be_reinvoice()
        )
