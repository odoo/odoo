from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("line_ids.purchase_line_ids.order_id.incoterm_location")
    def _compute_incoterm_location(self):
        super()._compute_incoterm_location()

    def _get_order_incoterm_locations(self):
        return [
            *super()._get_order_incoterm_locations(),
            *self.line_ids.purchase_line_ids.order_id.mapped("incoterm_location"),
        ]

    def _post_entries(self):

        _debug.pipeline("purchase_stock_entries_post", entries=self)
        if not self.env.context.get("move_reverse_cancel"):
            self.env["account.move.line"].create(
                self._stock_account_prepare_anglo_saxon_in_lines_vals(),
            )

        return super()._post_entries()

    def _stock_account_get_last_step_stock_moves(self):
        rslt = super()._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == "in_invoice"):
            rslt += invoice.mapped(
                "invoice_line_ids.purchase_line_ids.move_ids",
            ).filtered(
                lambda x: x.state == "done" and x.location_id.usage == "supplier",
            )
        for invoice in self.filtered(lambda x: x.move_type == "in_refund"):
            rslt += invoice.mapped(
                "invoice_line_ids.purchase_line_ids.move_ids",
            ).filtered(
                lambda x: x.state == "done" and x.location_dest_id.usage == "supplier",
            )
        return rslt

    def _stock_account_prepare_anglo_saxon_in_lines_vals(self):
        _debug.pipeline("anglo_saxon_in_lines_prepare", entries=self)
        lines_vals_list = []

        for move in self:
            if (
                move.move_type not in ("in_invoice", "in_refund", "in_receipt")
                or not move.company_id.anglo_saxon_accounting
            ):
                continue

            move = move.with_company(move.company_id)
            for line in move.invoice_line_ids:
                if (
                    not line._is_eligible_for_stock_account()
                    or line.product_id.cost_method != "standard"
                ):
                    continue

                debit_pdiff_account = move.fiscal_position_id.map_account(
                    line.product_id.categ_id.property_price_difference_account_id,
                )
                if not debit_pdiff_account:
                    continue

                price_unit_val_dif, relevant_qty = (
                    line._get_price_unit_val_dif_and_relevant_qty()
                )
                price_subtotal = relevant_qty * price_unit_val_dif

                if not move.currency_id.is_zero(price_subtotal):
                    lines_vals_list += [
                        line._prepare_price_difference_vals(
                            relevant_qty,
                            relevant_qty * price_unit_val_dif,
                            debit_pdiff_account,
                        ),
                        line._prepare_price_difference_vals(
                            relevant_qty,
                            relevant_qty * -price_unit_val_dif,
                            line.account_id,
                        ),
                    ]
        return lines_vals_list
