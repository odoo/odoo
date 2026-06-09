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

    @api.depends("website_track_ids")
    def _compute_slide_statistics(self):
        mapped_data = self._get_visitor_statistics(
            rel_model='slide.channel',
        )
        for visitor in self:
            stats = mapped_data.get(visitor.id, {'ids': [], 'count': 0})
            visitor.slide_channel_ids = [(6, 0, stats['ids'])]
            visitor.visitor_slide_count = stats['count']
