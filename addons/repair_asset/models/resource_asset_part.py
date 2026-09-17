from odoo import fields, models
from odoo.fields import Domain


class ResourceAssetPart(models.Model):
    _inherit = "resource.asset.part"

    # FIELDS
    source = fields.Selection(
        selection_add=[("repair", "Repair")],
        ondelete={"repair": "set default"},
    )
    repair_order_id = fields.Many2one(
        comodel_name="repair.order",
        index="btree_not_null",
        ondelete="restrict",
        check_company=True,
    )

    # HELPER METHODS
    def _get_domain_same_work(self):
        if self.repair_order_id:
            return Domain("repair_order_id", "=", self.repair_order_id.id)
        return super()._get_domain_same_work()
