from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    visitor_blog_count = fields.Integer(
        string="Blog Views",
        compute='_compute_blog_statistics',
    )
    blog_post_ids = fields.Many2many(
        comodel_name='blog.post',
        string="Blogs",
        compute='_compute_blog_statistics',
    )

    @api.depends("website_track_ids")
    def _compute_blog_statistics(self):
        mapped_data = self._get_visitor_statistics(
            rel_model='blog.post',
        )
        for visitor in self:
            stats = mapped_data.get(visitor.id, {'ids': [], 'count': 0})
            visitor.blog_post_ids = [(6, 0, stats['ids'])]
            visitor.visitor_blog_count = stats['count']
