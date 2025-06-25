from odoo import models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _get_layer_price_unit(self):
        """ This function returns the value of product in a layer per unit, relative to the aml
            the function is designed to be overriden to add logic to price unit calculation
        :param layer: the layer the price unit is derived from
        """
        return self.value / self.quantity

    def _get_related_product(self):
        res = super()._get_related_product()
        return self.stock_move_id.purchase_line_id.product_id if self.stock_move_id.purchase_line_id else res

    def _should_impact_price_unit_receipt_value(self):
        # In case of dropshipping, we only want the positive layers. When returned,
        # only the negative one matters
        res = super()._should_impact_price_unit_receipt_value()
        if not self.stock_move_id:
            return res

        return (
            res
            and (not self.stock_move_id._is_dropshipped() or self.value > 0)
            and (not self.stock_move_id._is_dropshipped_returned() or self.value < 0)
        )
