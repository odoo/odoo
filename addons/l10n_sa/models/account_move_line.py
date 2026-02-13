from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_discount_and_net_price(self):
        self.ensure_one()
        if self.discount != 100 and self.quantity:

            price_subtotal_before_discount = (
                (self.price_subtotal) / (1 - self.discount/1)
                if self.discount != 100
                else (self.price_unit * self.quantity)
            )

            print_unit = price_subtotal_before_discount / self.quantity

        else:

            price_subtotal_before_discount = self.price_unit * quantity

            print_unit = self.price_unit


        discount_amount = price_subtotal_before_discount - self.price_subtotal

        return {
            'discount_amount': discount_amount,
        }
