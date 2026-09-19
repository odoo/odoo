from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinBomComponent(models.AbstractModel):
    _name = "mixin.bom.component"
    _inherit = ["mixin.bom.variant.line"]
    _description = "A quantity of a product on a BoM"
    _rec_name = "product_id"
    _order = "sequence, id"
    _check_company_auto = True

    _bom_child_field = None

    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
        required=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related="bom_id.company_id",
        readonly=True,
    )
    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        default=1.0,
        required=True,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    sequence = fields.Integer(help="Gives the sequence order when displaying.")
    allowed_operation_ids = fields.One2many(
        comodel_name="mrp.routing.workcenter",
        related="bom_id.operation_ids",
    )
    operation_id = fields.Many2one(
        comodel_name="mrp.routing.workcenter",
        domain="[('id', 'in', allowed_operation_ids)]",
        check_company=True,
    )

    _qty_not_negative = models.Constraint(
        "CHECK (product_qty >= 0)",
        "A quantity on a bill of materials cannot be negative.",
    )

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for record in self:
            record.product_uom_id = record.product_id.uom_id

    @api.constrains("product_uom_id", "product_id")
    def _check_product_uom_id_category(self):
        for record in self:
            product_uom = record.product_id.uom_id
            if (
                record.product_uom_id
                and product_uom
                and not record.product_uom_id._has_common_reference(product_uom)
            ):
                _debug.logic(
                    "bom_component_refused",
                    reason="uom_category_mismatch",
                    record=record.id,
                    model=record._name,
                )
                raise ValidationError(record._get_uom_mismatch_message())

    def _get_uom_mismatch_message(self):
        raise NotImplementedError

    def action_add_from_catalog(self):
        bom = self.env["mrp.bom"].browse(self.env.context.get("order_id"))
        return bom.with_context(
            child_field=self._bom_child_field
        ).action_add_from_catalog()

    def _get_product_catalog_lines_data(self, **kwargs):
        if not self:
            return {"quantity": 0}
        self.product_id.check_singleton()
        return {
            **self[0].bom_id._get_product_price_and_data(self[0].product_id),
            "quantity": sum(
                self.mapped(
                    lambda line: line.product_uom_id._get_quantity_report(
                        qty=line.product_qty,
                        to_unit=line.product_id.uom_id,
                    )
                )
            ),
            "readOnly": len(self) > 1,
            "uomDisplayName": (len(self) == 1 and self.product_uom_id.display_name)
            or self.product_id.uom_id.display_name,
        }
