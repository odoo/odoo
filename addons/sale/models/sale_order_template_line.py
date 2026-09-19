from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _description = "Quotation Template Line"
    _order = "sale_order_template_id, sequence, id"

    _accountable_product_id_required = models.Constraint(
        "CHECK(display_type IS NOT NULL OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL))",
        "Missing required product and UoM on accountable sale quote line.",
    )
    _non_accountable_fields_null = models.Constraint(
        "CHECK(display_type IS NULL OR (product_id IS NULL AND product_uom_qty = 0 AND product_uom_id IS NULL))",
        "Forbidden product, quantity and UoM on non-accountable sale quote line",
    )

    sale_order_template_id = fields.Many2one(
        comodel_name="sale.order.template",
        string="Quotation Template Reference",
        index=True,
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(
        default=10,
        help="Gives the sequence order when displaying a list of sale quote lines.",
    )

    company_id = fields.Many2one(
        related="sale_order_template_id.company_id",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        domain=lambda self: self._domain_product_id(),
        check_company=True,
    )

    name = fields.Text(
        string="Description",
        translate=True,
    )

    allowed_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_uom_ids",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('id', 'in', allowed_uom_ids)]",
    )
    product_uom_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        default=1,
        required=True,
    )

    display_type = fields.Selection(
        selection=[
            ("line_section", "Section"),
            ("line_subsection", "Subsection"),
            ("line_note", "Note"),
        ],
        default=False,
    )

    parent_id = fields.Many2one(
        comodel_name="sale.order.template.line",
        string="Parent Section Line",
        compute="_compute_parent_id",
    )
    is_optional = fields.Boolean(
        string="Optional Line",
        default=False,
        copy=True,
    )

    @api.depends("product_id", "product_id.uom_id", "product_id.uom_ids")
    def _compute_allowed_uom_ids(self):
        for option in self:
            option.allowed_uom_ids = (
                option.product_id.uom_id | option.product_id.uom_ids
            )

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for option in self:
            option.product_uom_id = option.product_id.uom_id

    @api.depends(
        "display_type",
        "sequence",
        "sale_order_template_id.sale_order_template_line_ids.display_type",
        "sale_order_template_id.sale_order_template_line_ids.sequence",
    )
    def _compute_parent_id(self):
        option_lines = set(self)
        for template, lines in self.grouped("sale_order_template_id").items():
            if not template:
                lines.parent_id = False
                continue
            last_section = False
            last_sub = False
            for line in template.sale_order_template_line_ids.sorted("sequence"):
                if line.display_type == "line_section":
                    last_section = line
                    if line in option_lines:
                        line.parent_id = False
                    last_sub = False
                elif line.display_type == "line_subsection":
                    if line in option_lines:
                        line.parent_id = last_section
                    last_sub = line
                elif line in option_lines:
                    line.parent_id = last_sub or last_section

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get(
                "display_type", self.default_get(["display_type"])["display_type"]
            ):
                vals.update(product_id=False, product_uom_qty=0, product_uom_id=False)
        return super().create(vals_list)

    def write(self, vals):
        if "display_type" in vals and self.filtered(
            lambda line: line.display_type != vals.get("display_type")
        ):
            raise UserError(
                _(
                    "You cannot change the type of a sale quote line. Instead you should delete the current line and create a new line of the proper type."
                )
            )
        return super().write(vals)

    @api.model
    def _domain_product_id(self):
        return [("sale_ok", "=", True), ("type", "!=", "combo")]

    def _prepare_order_line_values(self):
        self.check_singleton()
        vals = {
            "display_type": self.display_type,
            "product_id": self.product_id.id,
            "product_qty": self.product_uom_qty,
            "product_uom_id": self.product_uom_id.id,
            "is_optional": self.is_optional,
            "sequence": self.sequence,
        }
        if self.name:
            vals["name"] = self.name
        return vals
