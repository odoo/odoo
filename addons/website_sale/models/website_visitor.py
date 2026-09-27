# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    visitor_product_count = fields.Integer(
        string="Product Views",
        help="Total number of views on products",
        compute="_compute_product_statistics",
    )
    product_ids = fields.Many2many(
        string="Visited Products",
        comodel_name="product.product",
        compute="_compute_product_statistics",
    )
    product_count = fields.Integer(
        string="Products Views",
        help="Total number of product viewed",
        compute="_compute_product_statistics",
    )

    @api.depends("website_track_ids")
    def _compute_product_statistics(self):
        mapped_data = self._get_visitor_statistics(
            "product_id",
            record_domain=self.env["product.product"]._check_company_domain(self.env.companies),
        )
        for visitor in self:
            visitor.product_ids = mapped_data[visitor.id]["ids"]
            visitor.visitor_product_count = mapped_data[visitor.id]["count"]
            visitor.product_count = len(mapped_data[visitor.id]["ids"])
