from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _is_downpayment(self):
        # OVERRIDE
        self.ensure_one()
        if sale_lines := self.pos_order_ids.lines.sale_order_line_id.filtered(lambda l: l.is_downpayment):
            if self.line_ids.filtered(lambda l: l.product_id in sale_lines.product_id and l.price_subtotal > 0):
                return True
        return super()._is_downpayment()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_downpayment_lines(self):
        # OVERRIDE  We try to find the original downpayment invoice line where the advance payment was made

        downpayment_products = self.env['pos.config'].sudo().search([]).mapped('down_payment_product_id')
        #lines_from_pos = self.filtered(lambda l: l.sale_line_ids and l.price_subtotal < 0 and l.product_id in downpayment_products)
        lines_from_pos = self.filtered(lambda l: l.move_id.pos_order_ids and l.price_subtotal < 0 and l.product_id in downpayment_products)
        total_lines = self.env['account.move.line']
        for line in lines_from_pos:
            sale_line = line.move_id.pos_order_ids.lines.filtered(lambda l: l.product_id == line.product_id).sale_order_line_id
            if len(sale_line) > 1: # If multiple downpayments, you have to choose the correct one
                result_sale_line =  sale_line.filtered(lambda sl: sl.price_unit == abs(line.price_subtotal))
                if not result_sale_line:
                    sale_line = sale_line[0]
                else:
                    sale_line = result_sale_line
                if len(result_sale_line) > 1:
                    # Make an order between things as there is not direct link between pos order lines and its linked invoice
                    move_lines = line.move_id.line_ids.filtered(lambda l: l.product_id == line.product_id and
                                                          line.price_subtotal == l.price_subtotal).sorted(lambda l: l.id).ids
                    move_line_idx = move_lines.index(line.id)
                    pos_order_lines = line.move_id.pos_order_ids.lines.filtered(lambda l: l.product_id == line.product_id and
                                                          line.price_subtotal == l.price_subtotal).sorted(lambda l: l.id)
                    if len(pos_order_lines) > move_line_idx:
                        sale_line = pos_order_lines[move_line_idx].sale_order_line_id
                    else:
                        sale_line = sale_line[0]
            lines = self.env['account.move.line']
            if sale_line and sale_line.is_downpayment:
                # Indirect, but direct to original downpayment
                lines = sale_line.invoice_lines.filtered(lambda l: l.move_id._is_downpayment())
                print(sale_line, sale_line.invoice_lines, lines)
                # Indirect Indirect
                indirect_line_invoice = sale_line.pos_order_line_ids.order_id.account_move
                downpayment_invoice = indirect_line_invoice.filtered(lambda inv: inv._is_downpayment())
                if downpayment_invoice:
                    lines |= downpayment_invoice.line_ids.filtered(lambda l: l.product_id == line.product_id)
            total_lines |= lines

        # Other pos lines stuff
        directly_linked_sale_lines = self.sale_line_ids.filtered('is_downpayment')
        for line in directly_linked_sale_lines:
            move = line.pos_order_line_ids.mapped('order_id').account_move
            if move and move._is_downpayment():
                total_lines |= move.line_ids.filtered(lambda l: l.product_id == line.product_id)

        # There is a 3rd case to tackle: if it was a regular invoice, but the original invoice came from PoS
        return super(AccountMoveLine, self - lines_from_pos)._get_downpayment_lines() | total_lines
