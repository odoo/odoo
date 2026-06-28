from odoo import fields, models


class StockZeroDemandConfirmation(models.TransientModel):
    _name = 'stock.zero.demand.confirmation'
    _description = 'Zero Demand Confirmation'

    picking_ids = fields.Many2many('stock.picking')

    def process(self):
        if self.picking_ids:
            if self.env.context.get('to_validate'):
                return self.picking_ids.with_context(skip_zero_demand_check=True).button_validate()
            return self.picking_ids.with_context(skip_zero_demand_check=True).action_confirm()
        return True

    def process_without_zero_moves(self):
        self.picking_ids.move_ids.filtered(lambda m: m.product_uom_qty <= 0).unlink()
        self.process()
