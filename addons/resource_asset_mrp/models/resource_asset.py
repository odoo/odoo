from odoo import fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    workcenter_id = fields.One2one(
        comodel_name="mrp.workcenter",
        inverse_name="asset_id",
        string="Work Center",
        context={"active_test": False},
    )
