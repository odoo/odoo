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
        self._compute_visitor_statistics(rel_field='blog_post_ids', rel_model='blog.post', count_field='visitor_blog_count')
