from odoo import api, fields, models
from odoo.tools.translate import LazyTranslate

from odoo.addons.team.models.team import TeamUsage

_lt = LazyTranslate(__name__)


class TeamTeam(models.Model):
    _inherit = "team.team"

    use_stock = fields.Boolean(
        string="Inventory",
        help="The team runs warehouse operations: operation types and their transfers belong to it.",
    )
    stock_picking_type_ids = fields.One2many(
        comodel_name="stock.picking.type",
        inverse_name="team_id",
        string="Operation Types",
    )

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "stock": TeamUsage(
                key="stock",
                flag="use_stock",
                label=_lt("Inventory"),
                manager_group="stock.group_stock_manager",
            ),
        }
