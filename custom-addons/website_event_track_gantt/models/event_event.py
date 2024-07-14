# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import api, fields, models


class Event(models.Model):
    _inherit = 'event.event'

    # Initial date and scale of the track gantt view
    track_gantt_initial_date = fields.Date(compute='_compute_track_gantt_information')
    track_gantt_scale = fields.Char(compute='_compute_track_gantt_information')

    @api.depends('track_ids.date', 'track_ids.date_end', 'date_begin', 'date_end')
    def _compute_track_gantt_information(self):
        for event in self:
            first_date = min([event.date_begin] + [track.date for track in event.track_ids if track.date])
            last_date = max([event.date_end] + [track.date_end for track in event.track_ids if track.date_end])

            if first_date and last_date:
                duration = last_date - first_date
                if duration / datetime.timedelta(days=30) > 1:
                    event.track_gantt_scale = 'year'
                elif duration / datetime.timedelta(weeks=1) > 1:
                    event.track_gantt_scale = 'month'
                elif duration / datetime.timedelta(days=1) > 1:
                    event.track_gantt_scale = 'week'
                else:
                    event.track_gantt_scale = 'day'

                event.track_gantt_initial_date = first_date
            else:
                event.track_gantt_scale = False
                event.track_gantt_initial_date = False
