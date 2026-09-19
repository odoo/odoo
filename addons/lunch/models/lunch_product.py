from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class LunchProduct(models.Model):
    """Products available to order. A product is linked to a specific vendor."""

    _name = "lunch.product"
    _description = "Lunch Product"
    _inherit = ["mixin.image", "mixin.user.favorite"]
    _order = "name"
    _check_company_auto = True

    name = fields.Char(
        string="Product Name",
        translate=True,
        required=True,
    )
    category_id = fields.Many2one(
        comodel_name="lunch.product.category",
        string="Product Category",
        required=True,
        check_company=True,
    )
    description = fields.Html(translate=True)
    price = fields.Float(
        digits="Account",
        required=True,
    )
    supplier_id = fields.Many2one(
        comodel_name="lunch.supplier",
        string="Vendor",
        required=True,
        check_company=True,
    )
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="supplier_id.company_id",
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )

    new_until = fields.Date()
    is_new = fields.Boolean(compute="_compute_is_new")

    favorite_user_ids = fields.Many2many(check_company=True)

    last_order_date = fields.Date(compute="_compute_last_order_date")

    product_image = fields.Image(compute="_compute_product_image")
    # This field is used only for searching
    is_available_at = fields.Many2one(
        comodel_name="lunch.location",
        string="Product Availability",
        compute="_compute_is_available_at",
        search="_search_is_available_at",
    )

    @api.depends("image_128", "category_id.image_128")
    def _compute_product_image(self):
        for product in self:
            product.product_image = product.image_128 or product.category_id.image_128

    @api.depends("new_until")
    def _compute_is_new(self):
        today = fields.Date.context_today(self)
        for product in self:
            if product.new_until:
                product.is_new = today <= product.new_until
            else:
                product.is_new = False

    @api.depends_context("uid")
    def _compute_last_order_date(self):
        all_orders = self.env["lunch.order"].search(
            [
                ("user_id", "=", self.env.user.id),
                ("product_id", "in", self.ids),
            ]
        )
        mapped_orders = defaultdict(lambda: self.env["lunch.order"])
        for order in all_orders:
            mapped_orders[order.product_id] |= order
        for product in self:
            if not mapped_orders[product]:
                product.last_order_date = False
            else:
                product.last_order_date = max(mapped_orders[product].mapped("date"))

    def _compute_is_available_at(self):
        """
        Is available_at is always false when browsing it
        this field is there only to search (see _search_is_available_at)
        """
        self.is_available_at = False

    def _search_is_available_at(self, operator, value):
        if operator != "in":
            return NotImplemented
        return Domain("supplier_id.available_location_ids", "in", value) | Domain(
            "supplier_id.available_location_ids", "=", False
        )

    def _sync_active_from_related(self):
        """Archive/unarchive product after related field is archived/unarchived"""
        self.filtered(
            lambda p: p.active and not (p.category_id.active and p.supplier_id.active)
        ).action_archive()
        self.filtered(
            lambda p: not p.active and (p.category_id.active and p.supplier_id.active)
        ).action_unarchive()

    @api.constrains("active", "category_id")
    def _check_active_categories(self):
        invalid_products = self.filtered(
            lambda product: product.active and not product.category_id.active
        )
        if invalid_products:
            raise UserError(
                _(
                    "The following product categories are archived. You should either unarchive the categories or change the category of the product.\n%s",
                    "\n".join(invalid_products.category_id.mapped("name")),
                )
            )

    @api.constrains("active", "supplier_id")
    def _check_active_suppliers(self):
        invalid_products = self.filtered(
            lambda product: product.active and not product.supplier_id.active
        )
        if invalid_products:
            raise UserError(
                _(
                    "The following suppliers are archived. You should either unarchive the suppliers or change the supplier of the product.\n%s",
                    "\n".join(invalid_products.supplier_id.mapped("name")),
                )
            )
