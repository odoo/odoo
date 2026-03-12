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

    @api.depends("website_track_ids")
    def _compute_product_statistics(self):
        # Get product IDs filtered by company
        product_query = self.env['product.product']._search(
            self.env['product.product']._check_company_domain(self.env.companies)
        )
        self._compute_visitor_statistics(
            rel_field='product_ids',
            rel_model='product.product',
            count_field='visitor_product_count',
            extra_domain=[
                ('res_id', 'in', product_query),
            ],
        )
