from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    visitor_product_count = fields.Integer(
        string="Product Views",
        compute="_compute_product_statistics",
        help="Total number of views on products",
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Visited Products",
        compute="_compute_product_statistics",
    )
    product_count = fields.Integer(
        string="# Visited Products",
        compute="_compute_product_statistics",
        help="Number of distinct products viewed",
    )

    @api.depends(
        "website_track_ids.product_id", "website_track_ids.product_id.company_id"
    )
    @api.depends_context("allowed_company_ids", "uid")
    def _compute_product_statistics(self):
        results = self.env["website.track"]._read_group(
            [
                ("visitor_id", "in", self.ids),
                ("product_id", "!=", False),
                (
                    "product_id",
                    "any",
                    self.env["product.product"]._check_company_domain(
                        self.env.companies
                    ),
                ),
            ],
            ["visitor_id"],
            ["product_id:recordset", "__count"],
        )
        mapped_data = {
            visitor.id: (products, count) for visitor, products, count in results
        }
        no_products = self.env["product.product"]
        for visitor in self:
            products, view_count = mapped_data.get(visitor.id, (no_products, 0))
            visitor.product_ids = products
            visitor.visitor_product_count = view_count
            visitor.product_count = len(products)

    def _add_viewed_product(self, product_id):
        self.check_singleton()
        if (
            product_id
            and self.env["product.product"].browse(product_id)._is_variant_possible()
        ):
            domain = [("product_id", "=", product_id)]
            website_track_values = {"product_id": product_id}
            self._add_tracking(domain, website_track_values)
