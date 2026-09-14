from odoo import api, fields, models
from odoo.tools.translate import LazyTranslate

from odoo.addons.team.models.team import TeamUsage

_lt = LazyTranslate(__name__)


class TeamTeam(models.Model):
    _inherit = "team.team"

    use_purchase = fields.Boolean(
        string="Purchase",
        help="The team buys: it owns purchase orders and vendor bills.",
    )
    purchase_order_ids = fields.One2many(
        comodel_name="purchase.order",
        inverse_name="team_id",
        string="Purchase Orders",
    )

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "purchase": TeamUsage(
                key="purchase",
                flag="use_purchase",
                label=_lt("Purchase"),
                manager_group="purchase.group_purchase_manager",
            ),
        }
