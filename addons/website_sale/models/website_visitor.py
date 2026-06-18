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
        mapped_data = self._get_visitor_statistics(
            rel_model='product.product',
            extra_domain=[
                ('res_id', 'in', product_query),
            ],
        )
        for visitor in self:
            stats = mapped_data.get(visitor.id, {'ids': [], 'count': 0})
            visitor.product_ids = [(6, 0, stats['ids'])]
            visitor.visitor_product_count = stats['count']
