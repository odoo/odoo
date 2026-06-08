# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _description = "Quotation Template Line"
    _order = "sale_order_template_id, sequence, id"

    _accountable_product_id_required = models.Constraint(
        "CHECK(display_type IS NOT NULL OR product_uom_id IS NOT NULL)",
        "Missing required UoM on accountable sale quote line.",
    )
    _non_accountable_fields_null = models.Constraint(
        "CHECK(display_type IS NULL OR (product_id IS NULL AND product_uom_qty = 0 AND product_uom_id IS NULL))",  # noqa: E501
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
        string="Sequence",
        help="Gives the sequence order when displaying a list of sale quote lines.",
        default=10,
    )

    company_id = fields.Many2one(
        related="sale_order_template_id.company_id", store=True, index=True
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        check_company=True,
        domain=lambda self: self._product_id_domain(),
    )

    name = fields.Text(string="Description", translate=True)

    allowed_uom_ids = fields.Many2many("uom.uom", compute="_compute_allowed_uom_ids")
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        domain="[('id', 'in', allowed_uom_ids)] if allowed_uom_ids or mandatory_product else []",
        compute="_compute_product_uom_id",
        store=True,
        readonly=False,
        precompute=True,
    )
    product_uom_qty = fields.Float(
        string="Quantity", required=True, digits="Product Unit", default=1
    )

    display_type = fields.Selection(
        [("line_section", "Section"), ("line_subsection", "Subsection"), ("line_note", "Note")],
        default=False,
    )

    # Section-related fields
    parent_id = fields.Many2one(
        string="Parent Section Line",
        comodel_name="sale.order.template.line",
        compute="_compute_parent_id",
    )
    is_optional = fields.Boolean(string="Optional Line", copy=True, default=False)
    collapse_composition = fields.Boolean()
    collapse_prices = fields.Boolean()

    # Technical fields which stores values for product SO line without product_id
    discount = fields.Float(string="Discount (%)", digits="Discount")
    price_unit = fields.Float(
        string="Unit Price", digits="Product Price", min_display_digits="Product Price"
    )
    tax_ids = fields.Many2many(string="Taxes", comodel_name="account.tax", check_company=True)

    mandatory_product = fields.Boolean(
        string="Is Product Mandatory", compute="_compute_mandatory_product"
    )

    # === COMPUTE METHODS ===#

    @api.depends("product_id")
    def _compute_allowed_uom_ids(self):
        for option in self:
            option.allowed_uom_ids = option.product_id._get_available_uoms()

    @api.depends("product_id", "display_type")
    def _compute_product_uom_id(self):
        unit_uom = self.env["product.template"]._default_uom_id()
        for option in self:
            if option.display_type:
                option.product_uom_id = False
            elif not option.product_id:
                option.product_uom_id = unit_uom
            else:
                option.product_uom_id = option.product_id.uom_id

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

    def _compute_mandatory_product(self):
        self.mandatory_product = (
            self.env["ir.config_parameter"].sudo().get_bool("sale.mandatory_product")
        )

    # === CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type", self.default_get(["display_type"])["display_type"]):
                vals.update(product_id=False, product_uom_qty=0, product_uom_id=False)
        return super().create(vals_list)

    def write(self, vals):
        if "display_type" in vals and self.filtered(
            lambda line: line.display_type != vals.get("display_type")
        ):
            raise UserError(
                self.env._(
                    "You cannot change the type of a sale quote line. Instead you should delete the"
                    " current line and create a new line of the proper type."
                )
            )
        return super().write(vals)

    # === BUSINESS METHODS ===#

    @api.model
    def _product_id_domain(self):
        """Return the domain of the products that can be added to the template."""
        return [("sale_ok", "=", True), ("type", "!=", "combo")]

    def _prepare_order_line_values(self, fiscal_position, currency):
        """Prepare values to create a sale order line from a template line.

        Line without products take price, discount, taxes from itself otherwise compute it based on
        product and related values.

        :param account.fiscal.position fiscal_position_id: fiscal position to use
        :param res.currency currency: target currency (of the order)

        :return: `sale.order.line` create values
        :rtype: dict
        """
        self.ensure_one()
        vals = {
            "collapse_composition": self.collapse_composition,
            "collapse_prices": self.collapse_prices,
            "display_type": self.display_type,
            "is_optional": self.is_optional,
            "product_id": self.product_id.id,
            "product_uom_qty": self.product_uom_qty,
            "product_uom_id": self.product_uom_id.id,
            "sequence": self.sequence,
        }
        if self.name:
            vals["name"] = self.name
            if self.product_id:
                vals["name"] = f"{self.product_id.display_name}\n{self.name}"

        if not self.product_id:
            taxes = self.tax_ids._filter_taxes_by_company()

            if fiscal_position:
                taxes = fiscal_position.map_tax(taxes)

            vals.update({
                "tax_ids": [Command.set(taxes.ids)],
                "discount": self.discount,
                "price_unit": self.sale_order_template_id.currency_id._convert(
                    from_amount=self.price_unit, to_currency=currency
                ),
            })

        return vals
