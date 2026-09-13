from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class PosBill(models.Model):
    _name = "pos.bill"
    _order = "value"
    _description = "Coins/Bills"
    _inherit = ["mixin.pos.load"]

    name = fields.Char()
    value = fields.Float(
        digits=(16, 4),
        required=True,
    )
    pos_config_ids = fields.Many2many(
        comodel_name="pos.config",
        string="Point of Sales",
    )

    @api.model
    def name_create(self, name):
        try:
            value = float(name)
        except ValueError:
            raise UserError(
                _("The name of the Coins/Bills must be a number.")
            ) from None
        result = super().create({"name": name, "value": value})
        dbg.lifecycle.debug("pos.bill %s created from %r", dbg.rec(result), name)
        return result.id, result.display_name

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [
            "|",
            ("id", "in", config.default_bill_ids.ids),
            ("pos_config_ids", "=", False),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "name", "value"]
