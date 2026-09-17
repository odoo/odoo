from odoo import fields, models


class ResourceAssetKind(models.Model):
    _inherit = "resource.asset.kind"

    position_ids = fields.One2many(
        comodel_name="resource.asset.kind.position",
        inverse_name="kind_id",
        string="Part Positions",
    )
