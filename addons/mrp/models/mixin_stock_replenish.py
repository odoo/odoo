from odoo import api, fields, models


class MixinStockReplenish(models.AbstractModel):
    _inherit = "mixin.stock.replenish"

    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Material",
    )
    show_bom = fields.Boolean(compute="_compute_show_bom")

    @api.depends("route_id")
    def _compute_show_bom(self):
        for rec in self:
            rec.show_bom = rec._is_bom_shown(rec.route_id)

    def _is_bom_shown(self, route):
        return route._has_manufacture_rule()
