from odoo import models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.price_unit,
            quantity=self.qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )
