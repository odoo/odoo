# -*-  coding: utf-8 -*-

from odoo import api, fields, models, _


class KarmaTracking(models.Model):
    _inherit = 'gamification.karma.tracking'

    origin_type = fields.Selection(selection_add=[('post', 'Post')])
    originated_by_post_id = fields.Many2one('forum.post', 'Originated by Post', readonly=True)

    @api.depends('originated_by_post_id')
    def _compute_originated_by(self):
        forum_tracking = self.filtered(lambda tracking: tracking.originated_by_post_id)
        for track in forum_tracking:
            track.originated_by = track.originated_by_post_id.display_name
        return super(KarmaTracking, (self-forum_tracking))._compute_originated_by()

    @api.depends('originated_by_post_id')
    def _compute_origin_type(self):
        forum_tracking = self.filtered(lambda tracking: tracking.originated_by_post_id)
        for track in forum_tracking:
            track.origin_type = 'post'
        return super(KarmaTracking, (self-forum_tracking))._compute_origin_type()
