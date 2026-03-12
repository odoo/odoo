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
        self._compute_visitor_statistics(rel_field='slide_channel_ids', rel_model='slide.channel', count_field='visitor_slide_count')
