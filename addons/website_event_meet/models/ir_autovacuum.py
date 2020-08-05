# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, models, fields


class AutoVacuum(models.AbstractModel):
    _inherit = 'ir.autovacuum'

    _DELAY_CLEAN = datetime.timedelta(hours=4)

    @api.model
    def power_on(self, *args, **kwargs):
        """Archive all non-pinned room with 0 participant if nobody has joined it for a moment."""
        self.env["event.meeting.room"].sudo().search([
            ("is_pinned", "=", False),
            ("active", "=", True),
            ("room_participant_count", "=", 0),
            ("room_last_activity", "<", fields.Datetime.now() - self._DELAY_CLEAN),
        ]).active = False

        return super(AutoVacuum, self).power_on(*args, **kwargs)
