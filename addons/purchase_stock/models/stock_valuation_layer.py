from odoo import models
from odoo.addons import stock_account


class StockValuationLayer(stock_account.StockValuationLayer):

    def _get_layer_price_unit(self):
        """ This function returns the value of product in a layer per unit, relative to the aml
            the function is designed to be overriden to add logic to price unit calculation
        :param layer: the layer the price unit is derived from
        """
        return self.value / self.quantity
