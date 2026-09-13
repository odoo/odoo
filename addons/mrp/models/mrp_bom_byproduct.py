from odoo import _, fields, models


class MrpBomByproduct(models.Model):
    _name = "mrp.bom.byproduct"
    _inherit = ["mixin.bom.component"]
    _description = "Byproduct"

    _bom_child_field = "byproduct_ids"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="By-product",
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="BoM",
    )
    operation_id = fields.Many2one(
        comodel_name="mrp.routing.workcenter",
        string="Produced in Operation",
    )
    cost_share = fields.Float(
        string="Cost Share (%)",
        digits=(5, 2),
        help="The percentage of the final production cost for this by-product line (divided between the quantity produced)."
        "The total of all by-products' cost share must be less than or equal to 100.",
    )

    def _get_uom_mismatch_message(self):
        return _(
            "The by-product %(product)s is produced in %(unit)s, which"
            " does not measure the same thing as its own unit"
            " %(product_unit)s.",
            product=self.product_id.display_name,
            unit=self.product_uom_id.display_name,
            product_unit=self.product_id.uom_id.display_name,
        )
