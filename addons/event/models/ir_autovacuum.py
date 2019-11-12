# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields


class AutoVacuum(models.AbstractModel):
    _inherit = 'ir.autovacuum'

    @api.model
    def power_on(self, *args, **kwargs):
        """
        Cron which drags all events which end date is < now (= passed)
        into the first next (by sequence) stage defined as "Ended"
        (if they are not already in an ended stage)
        """
        ended_events = self.env['event.event'].search([('date_end', '<', fields.Datetime.now()), ('stage_id.pipe_end', '=', False)])

        if ended_events:
            ended_events.action_set_done()

        return super(AutoVacuum, self).power_on(*args, **kwargs)
