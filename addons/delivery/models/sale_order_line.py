# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_delivery = fields.Boolean(string="Is a Delivery", default=False)
    product_qty = fields.Float(
        string='Product Qty', compute='_compute_product_qty', digits='Product Unit of Measure'
    )
    recompute_delivery_price = fields.Boolean(related='order_id.recompute_delivery_price')

    def _is_not_sellable_line(self):
        return self.is_delivery or super()._is_not_sellable_line()

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        for line in self:
            if not line.product_id or not line.product_uom or not line.product_uom_qty:
                line.product_qty = 0.0
                continue
            line.product_qty = line.product_uom._compute_quantity(
                line.product_uom_qty, line.product_id.uom_id
            )

    def unlink(self):
        for line in self:
            if line.is_delivery:
                line.order_id.carrier_id = False
        return super().unlink()

    def _is_delivery(self):
        self.ensure_one()
        return self.is_delivery

    # override to allow deletion of delivery line in a confirmed order
    def _check_line_unlink(self):
        """
        Extend the allowed deletion policy of SO lines.

        Lines that are delivery lines can be deleted from a confirmed order.

        :rtype: recordset sale.order.line
        :returns: set of lines that cannot be deleted
        """

        undeletable_lines = super()._check_line_unlink()
        return undeletable_lines.filtered(lambda line: not line.is_delivery)
