# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarProviderConfig(models.TransientModel):
    _name = 'calendar.popover.delete.wizard'
    _description = 'Calendar Popover Delete Wizard'


    record = fields.Many2one('calendar.event', 'Calendar Event')
    delete = fields.Selection([('one', 'Delete this event'), ('next', 'Delete this and following events'), ('all', 'Delete all the events')], default='one')

    def close(self):
        if not self.record or not self.delete:
            pass
        elif self.delete == 'one':
            self.record.unlink()
        else:
            switch = {
                'next': 'future_events',
                'all': 'all_events'
            }
            self.record.action_mass_deletion(switch.get(self.delete, ''))
