# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ProductSupplierinfo(models.Model):
    _name = "product.supplierinfo"
    _description = "Supplier Pricelist"
    _order = "sequence, min_qty DESC, price, id"
    _rec_name = "partner_id"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        required=True,
        check_company=True,
        ondelete="cascade",
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
        string="Sequence",
        default=1,
        help="Assigns the priority to the list of product vendor.",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        required=True,
        compute="_compute_product_uom_id",
        store=True,
        precompute=True,
        readonly=False,
    )
    min_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        required=True,
        default=0.0,
        help="The quantity to purchase from this vendor to benefit from the unit price. If a vendor unit is set, quantity should be specified in this unit, otherwise it should be specified in the default unit of the product.",
    )
    price = fields.Float(
        string="Unit Price",
        digits="Product Price",
        default=0.0,
        help="The price to purchase a product",
    )
    price_discounted = fields.Float(
        string="Discounted Price",
        compute="_compute_price_discounted",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company.id,
        index=1,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    date_start = fields.Date(
        string="Start Date",
        help="Start date for this vendor price",
    )
    date_end = fields.Date(string="End Date", help="End date for this vendor price")
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product Variant",
        compute="_compute_product_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
        domain="[('product_tmpl_id', '=', product_tmpl_id)] if product_tmpl_id else []",
        help="If not set, the vendor price will apply to all variants of this product.",
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        required=True,
        compute="_compute_product_tmpl_id",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
        ondelete="cascade",
        index=True,
    )
    product_variant_count = fields.Integer(
        related="product_tmpl_id.product_variant_count",
        string="Variant Count",
    )
    delay = fields.Integer(
        string="Lead Time",
        required=True,
        default=1,
        help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.",
    )
    discount = fields.Float(string="Discount (%)", digits="Discount", readonly=False)

    @api.depends("product_id", "product_tmpl_id")
    def _compute_product_uom_id(self):
        for rec in self:
            if not rec.product_uom_id:
                rec.product_uom_id = (
                    rec.product_id.uom_id
                    if rec.product_id
                    else rec.product_tmpl_id.uom_id
                )

    @api.depends("product_id", "product_tmpl_id")
    def _compute_price(self):
        for rec in self:
            rec.price = (
                rec.product_id.standard_price
                if rec.product_id
                else rec.product_tmpl_id.standard_price if rec.product_tmpl_id else 0.0
            )

    @api.depends("discount", "price")
    def _compute_price_discounted(self):
        for rec in self:
            product_uom = (rec.product_id or rec.product_tmpl_id).uom_id
            rec.price_discounted = rec.product_uom_id._compute_price(
                rec.price,
                product_uom,
            ) * (1 - rec.discount / 100)

    @api.depends("product_id")
    def _compute_product_tmpl_id(self):
        for rec in self:
            if rec.product_id:
                rec.product_tmpl_id = rec.product_id.product_tmpl_id

    @api.depends("product_id", "product_tmpl_id", "product_variant_count")
    def _compute_product_id(self):
        for rec in self:
            if self.env.get("default_product_id"):
                rec.product_id = self.env.get("default_product_id")
            elif not rec.product_id and rec.product_variant_count == 1:
                rec.product_id = rec.product_tmpl_id.product_variant_id

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id(self):
        """Clear product variant if it no longer matches the product template."""
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

    def _sanitize_vals(self, vals):
        """Sanitize vals to sync product variant & template on read/write."""
        # add product's product_tmpl_id if none present in vals
        if vals.get("product_id") and not vals.get("product_tmpl_id"):
            product = self.env["product.product"].browse(vals["product_id"])
            vals["product_tmpl_id"] = product.product_tmpl_id.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sanitize_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._sanitize_vals(vals)
        return super().write(vals)

    def _get_filtered_supplier(self, company_id, product_id, params=False):
        return self.filtered(
            lambda s: (not s.company_id or s.company_id.id == company_id.id)
            and (
                s.partner_id.active and (not s.product_id or s.product_id == product_id)
            )
        )
