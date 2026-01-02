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

    @api.depends('website_track_ids')
    def _compute_blog_statistics(self):
        results = self.env['website.track']._read_group([
            ('visitor_id', 'in', self.ids),
            ('blog_post_id', '!=', False),
        ], ['visitor_id'], ['blog_post_id:array_agg', '__count'])
        mapped_data = {
            visitor.id: {'visitor_blog_count': count, 'blog_post_ids': blog_post_ids}
            for visitor, blog_post_ids, count in results
        }

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'blog_post_ids': [], 'visitor_blog_count': 0})
            visitor.blog_post_ids = [(6, 0, visitor_info['blog_post_ids'])]
            visitor.visitor_blog_count = len(visitor_info['blog_post_ids'])

    def _add_viewed_blog(self, blog_post_id):
        """ add a website_track with a page marked as viewed"""
        self.ensure_one()
        if blog_post_id:
            domain = [('blog_post_id', '=', blog_post_id)]
            website_track_values = {'blog_post_id': blog_post_id}
            self._add_tracking(domain, website_track_values)
