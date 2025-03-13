from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_downpayment_lines(self):
        # OVERRIDE so we can play with downpayments that are not linked to an original invoice
        downpayment_products = self.env['pos.config'].sudo().search([]).mapped('down_payment_product_id')
        lines_from_pos = self.filtered(lambda l: l.sale_line_ids and l.price_subtotal < 0 and l.product_id in downpayment_products)
        return super(AccountMoveLine, self - lines_from_pos)._get_downpayment_lines() | lines_from_pos
