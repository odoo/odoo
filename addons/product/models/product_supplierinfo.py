from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductSupplierinfo(models.Model):
    _name = "product.supplierinfo"
    _description = "Supplier Pricelist"
    _order = "sequence, min_qty DESC, price, id"
    _rec_name = "partner_id"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    product_name = fields.Char(
        string="Vendor Product Name",
        help="This vendor's product name will be used when printing a request for quotation. Keep empty to use the internal one.",
    )
    product_code = fields.Char(
        string="Vendor Product Code",
        help="This vendor's product code will be used when printing a request for quotation. Keep empty to use the internal one.",
    )
    sequence = fields.Integer(
        default=1,
        help="Assigns the priority to the list of product vendor.",
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
    min_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        default=0.0,
        required=True,
        help="The quantity to purchase from this vendor to benefit from the unit price. If a vendor unit is set, quantity should be specified in this unit, otherwise it should be specified in the default unit of the product.",
    )
    price = fields.Float(
        string="Unit Price",
        min_display_digits="Product Price",
        default=0.0,
        help="The price to purchase a product",
    )
    price_discounted = fields.Float(
        string="Discounted Price",
        compute="_compute_price_discounted",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        index=1,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )
    date_start = fields.Date(
        string="Start Date",
        help="Start date for this vendor price",
    )
    date_end = fields.Date(
        string="End Date",
        help="End date for this vendor price",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product Variant",
        compute="_compute_product_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('product_tmpl_id', '=', product_tmpl_id)] if product_tmpl_id else []",
        check_company=True,
        help="If not set, the vendor price will apply to all variants of this product.",
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        compute="_compute_product_tmpl_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    product_variant_count = fields.Integer(
        related="product_tmpl_id.product_variant_count",
        string="Variant Count",
    )
    delay = fields.Integer(
        string="Lead Time",
        default=1,
        required=True,
        help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.",
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        readonly=False,
    )

    @api.depends("product_id", "product_tmpl_id")
    def _compute_product_uom_id(self):
        for rec in self:
            if not rec.product_uom_id:
                rec.product_uom_id = (
                    rec.product_id.uom_id
                    if rec.product_id
                    else rec.product_tmpl_id.uom_id
                )

    @api.depends(
        "discount", "price", "product_uom_id", "product_id", "product_tmpl_id.uom_id"
    )
    def _compute_price_discounted(self):
        for rec in self:
            product_uom_id = (rec.product_id or rec.product_tmpl_id).uom_id
            rec.price_discounted = rec.product_uom_id._get_price_estimate(
                rec.price,
                product_uom_id,
            ) * (1 - rec.discount / 100)

    @api.depends("product_id")
    def _compute_product_tmpl_id(self):
        for rec in self:
            if rec.product_id:
                rec.product_tmpl_id = rec.product_id.product_tmpl_id

    @api.depends("product_tmpl_id")
    def _compute_product_id(self):
        default_product = self.env["product.product"].browse(
            self.env.context.get("default_product_id")
        )
        for rec in self:
            if (
                not rec.product_id
                and default_product
                and default_product.product_tmpl_id == rec.product_tmpl_id
            ):
                rec.product_id = default_product

    @api.constrains("product_id", "product_tmpl_id")
    def _check_product_variant_consistency(self):
        for rec in self:
            if rec.product_id and rec.product_id.product_tmpl_id != rec.product_tmpl_id:
                raise ValidationError(
                    self.env._(
                        "The product variant %(variant)s does not belong to the"
                        " product %(product)s.",
                        variant=rec.product_id.display_name,
                        product=rec.product_tmpl_id.display_name,
                    )
                )

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(
                    self.env._(
                        "The end date of vendor %(vendor)s must be after its"
                        " start date.",
                        vendor=rec.partner_id.display_name,
                    )
                )

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id(self):
        if (
            self.product_id
            and self.product_id not in self.product_tmpl_id.product_variant_ids
        ):
            self.product_id = False

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Vendor Pricelists"),
                "template": "/product/static/xls/product_supplierinfo.xls",
            }
        ]

    def _normalize_vals(self, vals):
        if vals.get("product_id") and not vals.get("product_tmpl_id"):
            product = self.env["product.product"].browse(vals["product_id"])
            return {**vals, "product_tmpl_id": product.product_tmpl_id.id}
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._normalize_vals(vals) for vals in vals_list])

    def write(self, vals):
        return super().write(self._normalize_vals(vals))

    def _filtered_for_company_and_product(self, company_id, product_id, params=False):
        return self.filtered(
            lambda s: (
                (not s.company_id or s.company_id.id == company_id.id)
                and (
                    s.partner_id.sudo().active
                    and (not s.product_id or s.product_id == product_id)
                )
            )
        )
