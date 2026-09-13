from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_repair_line = fields.Boolean(
        string="Is linked to repair",
        compute="_compute_is_repair_line",
    )

    @api.depends("move_ids.repair_id")
    def _compute_is_repair_line(self):
        for so_line in self:
            so_line.is_repair_line = bool(
                so_line.move_ids.sudo().filtered(lambda m: m.repair_id)
            )

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        result += ["is_repair_line"]
        return result
