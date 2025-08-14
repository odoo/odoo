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
