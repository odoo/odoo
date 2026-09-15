from odoo import fields, models


class ResourceAssetKind(models.Model):
    _inherit = "resource.asset.kind"

    technician_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Technician",
        help="Maintains the assets of this kind unless an asset names its own technician.",
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="team.team",
        domain=[("use_maintenance", "=", True)],
        help="Receives the maintenance of the assets of this kind unless an asset names its own team.",
    )
