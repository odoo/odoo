from odoo import fields, models


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

    def _compute_blog_statistics(self):
        self._compute_visitor_agg(field_name='blog_post_ids', rel_field='blog_post_id', count_field='visitor_blog_count')

    def _add_viewed_blog(self, blog_post_id):
        """ add a website_track with a page marked as viewed"""
        self.ensure_one()
        if blog_post_id:
            domain = [('blog_post_id', '=', blog_post_id)]
            website_track_values = {'blog_post_id': blog_post_id}
            self._add_tracking(domain, website_track_values)
