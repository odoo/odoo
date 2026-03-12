# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    visitor_blog_post_count = fields.Integer(
        string="Blog Post Views",
        help="Total number of views on blog posts",
        compute='_compute_blog_post_statistics',
    )
    blog_post_ids = fields.Many2many(
        comodel_name='blog.post',
        string="Blog Posts",
        compute='_compute_blog_post_statistics',
    )

    @api.depends('website_track_ids')
    def _compute_blog_post_statistics(self):
        mapped_data = self._get_visitor_statistics('blog_post_id')
        for visitor in self:
            visitor.blog_post_ids = mapped_data[visitor.id]['ids']
            visitor.visitor_blog_post_count = mapped_data[visitor.id]['count']
