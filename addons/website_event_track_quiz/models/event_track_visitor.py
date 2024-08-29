# -*- coding: utf-8 -*-
from odoo.addons import website_event_track
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventTrackVisitor(models.Model, website_event_track.EventTrackVisitor):

    quiz_completed = fields.Boolean('Completed')
    quiz_points = fields.Integer("Quiz Points", default=0)
