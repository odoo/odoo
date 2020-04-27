# -*-  coding: utf-8 -*-

from odoo import api, fields, models, _


class KarmaTracking(models.Model):
    _inherit = 'gamification.karma.tracking'

    origin_type = fields.Selection(selection_add=[('quiz', 'Quiz'), ('course', 'Course')])
    originated_by_slide_channel_id = fields.Many2one('slide.channel', 'Originated by Course', readonly=True)
    originated_by_slide_id = fields.Many2one('slide.slide', 'Originated by Quiz', readonly=True)

    @api.depends('originated_by_slide_channel_id', 'originated_by_slide_id')
    def _compute_originated_by(self):
        slides_channel_tracking = self.filtered(lambda tracking: tracking.originated_by_slide_channel_id)
        for track in slides_channel_tracking:
            track.originated_by = track.originated_by_slide_channel_id.display_name
        slides_tracking = self.filtered(lambda tracking: tracking.originated_by_slide_id)
        for track in slides_tracking:
            track.originated_by = track.originated_by_slide_id.display_name
        return super(KarmaTracking, (self - slides_tracking - slides_channel_tracking))._compute_originated_by()

    @api.depends('originated_by_slide_channel_id')
    def _compute_origin_type(self):
        slides_channel_tracking = self.filtered(lambda tracking: tracking.originated_by_slide_channel_id)
        for track in slides_channel_tracking:
            track.origin_type = 'course'
        slides_tracking = self.filtered(lambda tracking: tracking.originated_by_slide_id)
        for track in slides_tracking:
            track.origin_type = 'quiz'
        return super(KarmaTracking, (self - slides_tracking - slides_channel_tracking))._compute_origin_type()
