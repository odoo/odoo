# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SocialPost(models.Model):
    _inherit = "social.post"

    # Technical field that holds the relationship between a track and this 'reminder' post
    event_track_id = fields.Many2one('event.track', string="Linked Event Track",
        ondelete='cascade')
