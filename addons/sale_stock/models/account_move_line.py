from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_cogs_qty(self):
        self.check_singleton()
        valuation_account = self.product_id.product_tmpl_id._get_product_accounts(
            fiscal_pos=self.move_id.fiscal_position_id
        )["stock_valuation"]
        sale_lines = self.sale_line_ids
        posted_cogs_lines = sale_lines.order_id.invoice_ids.filtered(
            lambda m: m.move_type == "out_invoice"
        ).line_ids.filtered(
            lambda line: (
                line.display_type == "cogs"
                and line.account_id == valuation_account
                and line.cogs_origin_id.sale_line_ids & sale_lines
            )
        )
        posted_cogs_qty_prod_uom = sum(
            posted_cogs_lines.mapped(
                lambda line: (
                    line.product_uom_id._get_quantity_in_unit(
                        line.quantity, line.product_id.uom_id
                    )
                    * (-1 if line.move_id.move_type == "out_refund" else 1)
                )
            )
        )
        return posted_cogs_qty_prod_uom + super()._get_cogs_qty()

    def _get_posted_cogs_value(self):
        self.check_singleton()
        valuation_account = self.product_id.product_tmpl_id._get_product_accounts(
            fiscal_pos=self.move_id.fiscal_position_id
        )["stock_valuation"]
        sale_lines = self.sale_line_ids
        posted_cogs_value = -sum(
            sale_lines.order_id.invoice_ids.filtered(
                lambda m: m.move_type == "out_invoice"
            )
            .line_ids.filtered(
                lambda line: (
                    line.display_type == "cogs"
                    and line.account_id == valuation_account
                    and line.cogs_origin_id.sale_line_ids & sale_lines
                )
            )
            .mapped("balance")
        )
        return posted_cogs_value + super()._get_posted_cogs_value()

    def _get_stock_moves(self):
        return super()._get_stock_moves() | self._get_sale_stock_move()

    def _get_sale_stock_move(self):
        return self.sale_line_ids.move_ids

    def _get_lines_from_original_invoice(self):
        original_lines = super()._get_lines_from_original_invoice()
        if (
            self.move_id.move_type == "out_refund"
            and not self.move_id.reversed_entry_id
        ):
            original_lines += self.sale_line_ids.invoice_line_ids.move_id.filtered(
                lambda m: m.move_type == "out_invoice"
            ).line_ids.filtered(
                lambda line: (
                    line.display_type == "cogs"
                    and line.product_id == self.product_id
                    and line.product_uom_id == self.product_uom_id
                    and line.price_unit >= 0
                )
            )
        return original_lines

    def _sale_can_be_reinvoiced(self):
        self.check_singleton()
        return (
            self.move_type != "entry"
            and self.display_type != "cogs"
            and super()._sale_can_be_reinvoiced()
        )
