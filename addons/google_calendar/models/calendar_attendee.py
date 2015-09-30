# -*- coding: utf-8 -*-
from datetime import datetime

from openerp.osv import osv, fields


class calendar_attendee(osv.Model):
    _inherit = 'calendar.attendee'

    _columns = {
        'google_internal_event_id': fields.char('Google Calendar Event Id'),
        'oe_synchro_date': fields.datetime('Odoo Synchro Date'),
    }
    _sql_constraints = [('google_id_uniq', 'unique(google_internal_event_id,partner_id,event_id)', 'Google ID should be unique!')]

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}

        for id in ids:
            ref = vals.get('event_id', self.browse(cr, uid, id, context=context).event_id.id)

            # If attendees are updated, we need to specify that next synchro need an action
            # Except if it come from an update_from_google
            if not context.get('curr_attendee', False) and not context.get('NewMeeting', False):
                self.pool['calendar.event'].write(cr, uid, ref, {'oe_update_date': datetime.now()}, context)
        return super(calendar_attendee, self).write(cr, uid, ids, vals, context=context)