from odoo import models
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_downpayment_lines(self):
        # EXTENDS sale
        downpayment_lines = self.env["account.move.line"]
        if not self.env['pos.order.line'].has_access('read'):
            return super()._get_downpayment_lines()

        for record in self:
            rounding = record.currency_id.rounding
            if related_sol := record.sale_line_ids:
                # if order is not settled through POS
                # We're assuming that if an order is settled through POS it will have sale_line_ids empty.
                # We're also assuming that the downpayment line will have the same price_subtotal & tax_ids as the record.
                pos_downpayment_moves = related_sol.filtered("is_downpayment").pos_order_line_ids.order_id.account_move
                downpayment_lines |= pos_downpayment_moves.invoice_line_ids.filtered(
                    lambda r: float_compare(r.price_subtotal, -record.price_subtotal, precision_rounding=rounding) == 0
                    and r.tax_ids == record.tax_ids,
                )

            elif related_posl := record.move_id.pos_order_ids.lines:
                # if order is settled through POS
                # We get the downpayment lines through:
                # final invoice -> final POS order -> origin sale order -> downpayment pos order -> downpayment invoice
                sale_orders = related_posl.sale_order_origin_id
                candidate_moves = sale_orders.pos_order_line_ids.order_id.account_move.filtered(lambda r: r._is_downpayment())
                applicable_lines = candidate_moves.invoice_line_ids.filtered(
                    lambda line: float_compare(line.price_subtotal, -record.price_subtotal, precision_rounding=rounding) == 0
                    and line.tax_ids == record.tax_ids,
                )

                if len(applicable_lines) > 1:
                    # In the case there are multiple downpayment lines with the same tax & total we'll
                    # pair them up as per their ids and get the downpayment line paired with the record.
                    move_lines = record.move_id.invoice_line_ids
                    lines_dict = dict(zip(move_lines.sorted('id'), applicable_lines.sorted('id')))
                    downpayment_lines |= lines_dict.get(record)
                else:
                    downpayment_lines |= applicable_lines

        return downpayment_lines | super()._get_downpayment_lines()
