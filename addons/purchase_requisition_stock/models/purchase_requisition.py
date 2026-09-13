from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    def _default_picking_type_id(self):
        picking_type = self.env["stock.picking.type"].search(
            [
                ("warehouse_id.company_id", "=", self.env.company.id),
                ("code", "=", "incoming"),
            ],
            limit=1,
        )
        if not picking_type:
            self.env["stock.warehouse"]._raise_missing_warehouse()
        return picking_type

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        domain="[('company_id', '=', company_id)]",
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        default=_default_picking_type_id,
        required=True,
        domain="['|',('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
    )
