# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models


class EventMailScheduler(models.Model):
    """Clean the non-pinned old unused meeting rooms.

    Archive all non-pinned room with 0 participant if nobody has joined it for a moment.
    Run in the event mail CRON to avoid to create a new CRON (and to clean the meeting
    room every 2 hours).
    """

    _inherit = "event.mail"

    _DELAY_CLEAN = datetime.timedelta(hours=48)

    @api.model
    def run(self, autocommit=False):
        self.env["event.meeting.room"].sudo().search([
            ("is_pinned", "=", False),
            ("active", "=", True),
            ("room_participant_count", "=", 0),
            ("room_last_activity", "<", fields.Datetime.now() - self._DELAY_CLEAN),
        ]).active = False

        return super(EventMailScheduler, self).run(autocommit=autocommit)
