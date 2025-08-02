from odoo import models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _get_layer_price_unit(self):
        """ This function returns the value of product in a layer per unit, relative to the aml
            the function is designed to be overriden to add logic to price unit calculation
        :param layer: the layer the price unit is derived from
        """
        return self.value / self.quantity

    def _should_impact_price_unit_receipt_value(self):
        res = super()._should_impact_price_unit_receipt_value()
        negative_dropshipped_svl = self.stock_move_id._is_dropshipped() and self.value < 0
        return res and not negative_dropshipped_svl
