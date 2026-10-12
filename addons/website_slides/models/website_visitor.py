# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    visitor_slide_channel_count = fields.Integer(
        string="Course Views",
        help="Total number of views on courses",
        compute='_compute_slide_channel_statistics',
    )
    slide_channel_ids = fields.Many2many(
        comodel_name='slide.channel',
        string="Courses",
        compute='_compute_slide_channel_statistics',
    )

    @api.depends('website_track_ids')
    def _compute_slide_channel_statistics(self):
        mapped_data = self._get_visitor_statistics('slide_channel_id')
        for visitor in self:
            visitor.slide_channel_ids = mapped_data[visitor.id]['ids']
            visitor.visitor_slide_channel_count = mapped_data[visitor.id]['count']
