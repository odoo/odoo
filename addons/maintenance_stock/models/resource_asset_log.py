from odoo import fields, models


class ResourceAssetLog(models.Model):
    _inherit = "resource.asset.log"

    source = fields.Selection(
        selection_add=[("maintenance", "Maintenance")],
        ondelete={"maintenance": "set default"},
    )
    maintenance_order_id = fields.Many2one(
        comodel_name="maintenance.order",
        index="btree_not_null",
        ondelete="set null",
        help="The maintenance order whose returned equipment booked this entry.",
    )
