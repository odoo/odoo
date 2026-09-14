from odoo import api, fields, models
from odoo.tools.translate import LazyTranslate

from odoo.addons.team.models.team import TeamUsage

_lt = LazyTranslate(__name__)


class TeamTeam(models.Model):
    _inherit = "team.team"

    use_mrp = fields.Boolean(
        string="Manufacturing",
        help="The team manufactures: the orders of its operation types belong to it.",
    )
    mrp_production_ids = fields.One2many(
        comodel_name="mrp.production",
        inverse_name="team_id",
        string="Manufacturing Orders",
    )

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "mrp": TeamUsage(
                key="mrp",
                flag="use_mrp",
                label=_lt("Manufacturing"),
                manager_group="mrp.group_mrp_manager",
            ),
        }
