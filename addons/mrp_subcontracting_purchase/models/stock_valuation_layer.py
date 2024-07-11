

from odoo import models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _get_layer_price_unit(self):
        """ For a subcontracted product, we want a way to get the subcontracting cost (the price on the PO)
            This override deducts the value of subcomponents from the layer price.
        """
        components_price = 0
        production = self.stock_move_id.production_id
        if production.subcontractor_id and production.state == 'done':
            # each layer has a quantity and price for each move, to get the correct component price for each move
            # we need to get the components used for each quantity
            for move in production.move_raw_ids:
                components_price += sum(move.sudo().stock_valuation_layer_ids.mapped('value')) / production.product_uom_qty
        # the move valuation is negative (out moves) therefore we we add the negative components_price instead of subtracting
        return super()._get_layer_price_unit() + components_price
