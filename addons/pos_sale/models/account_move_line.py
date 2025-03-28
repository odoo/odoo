from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_downpayment_lines(self):
        # OVERRIDE so we can play with downpayments that are not linked to an original invoice
        # There are ... that we need to take care of

        #  return self.sale_line_ids.filtered('is_downpayment').invoice_lines.filtered(lambda line: line.move_id._is_downpayment())
        #for move in self:
        downpayment_products = self.env['pos.config'].sudo().search([]).mapped('down_payment_product_id')
        #lines_from_pos = self.filtered(lambda l: l.sale_line_ids and l.price_subtotal < 0 and l.product_id in downpayment_products)
        lines_from_pos = self.filtered(lambda l: l.move_id.pos_order_ids and l.price_subtotal < 0 and l.product_id in downpayment_products)
        total_lines = self.env['account.move.line']
        for line in lines_from_pos:
            sale_line = line.move_id.pos_order_ids.lines.filtered(lambda l: l.product_id == line.product_id).sale_order_line_id
            if sale_line.is_downpayment:
                lines = sale_line.invoice_lines.filtered(lambda l: l.move_id.is_downpayment())
                indirect_line_invoice = sale_line.pos_order_line_ids.order_id.account_move
                if indirect_line_invoice.is_downpayment:
                    lines |= indirect_line_invoice.line_ids.filtered(lambda l: l.product_id == line.product_id)
            total_lines |= lines

        # Other pos lines stuff
        directly_linked_sale_lines = self.sale_line_ids.filtered('is_downpayment')
        for line in directly_linked_sale_lines:
            move = line.pos_order_line_ids.mapped('order_id').account_move
            if move._is_downpayment():
                total_lines |= move.line_ids.filtered(lambda l: l.product_id == line.product_id)

        # There is a 3rd case to tackle: if it was a regular invoice, but the original invoice came from PoS
        return super(AccountMoveLine, self - lines_from_pos)._get_downpayment_lines() | total_lines
