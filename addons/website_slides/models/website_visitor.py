from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    visitor_slide_count = fields.Integer(
        string="Slide Views",
        compute='_compute_slide_statistics',
    )
    slide_channel_ids = fields.Many2many(
        comodel_name='slide.channel',
        string="Slides",
        compute='_compute_slide_statistics',
    )

    @api.depends('website_track_ids')
    def _compute_slide_statistics(self):
        results = self.env['website.track']._read_group([
            ('visitor_id', 'in', self.ids),
            ('slide_channel_id', '!=', False),
        ], ['visitor_id'], ['slide_channel_id:array_agg', '__count'])
        mapped_data = {
            visitor.id: {'visitor_slide_count': count, 'slide_channel_ids': slide_channel_ids}
            for visitor, slide_channel_ids, count in results
        }

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'slide_channel_ids': [], 'visitor_slide_count': 0})
            visitor.slide_channel_ids = [(6, 0, visitor_info['slide_channel_ids'])]
            visitor.visitor_slide_count = len(visitor_info['slide_channel_ids'])

    def _add_viewed_slide(self, slide_channel_id):
        """ add a website_track with a page marked as viewed"""
        self.ensure_one()
        if slide_channel_id:
            domain = [('slide_channel_id', '=', slide_channel_id)]
            website_track_values = {'slide_channel_id': slide_channel_id}
            self._add_tracking(domain, website_track_values)
