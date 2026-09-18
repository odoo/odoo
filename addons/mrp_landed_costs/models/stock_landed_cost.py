from odoo import fields, models


class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    mrp_production_ids = fields.Many2many(
        comodel_name="mrp.production",
        string="Manufacturing order",
        copy=False,
        groups="stock.group_stock_manager",
    )

    def _get_targeted_move_ids(self):
        return (
            super()._get_targeted_move_ids()
            | self.mrp_production_ids.move_finished_ids
            - self.mrp_production_ids.move_byproduct_ids.filtered(
                lambda move: not move.cost_share
            )
        )
