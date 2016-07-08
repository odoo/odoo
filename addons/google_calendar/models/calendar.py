# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datatime import datetime
from openerp.osv import fields, osv

import logging
_logger = logging.getLogger(__name__)


class calendar_event(osv.Model):
    _inherit = "calendar.event"

    def get_fields_need_update_google(self, cr, uid, context=None):
        recurrent_fields = self._get_recurrent_fields(cr, uid, context=context)
        return recurrent_fields + ['name', 'description', 'allday', 'start', 'date_end', 'stop',
                                   'attendee_ids', 'alarm_ids', 'location', 'class', 'active',
                                   'start_date', 'start_datetime', 'stop_date', 'stop_datetime']

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        sync_fields = set(self.get_fields_need_update_google(cr, uid, context))
        if (set(vals.keys()) & sync_fields) and 'oe_update_date' not in vals.keys() and 'NewMeeting' not in context:
            vals['oe_update_date'] = datetime.now()

        return super(calendar_event, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        if default.get('write_type', False):
            del default['write_type']
        elif default.get('recurrent_id', False):
            default['oe_update_date'] = datetime.now()
        else:
            default['oe_update_date'] = False
        return super(calendar_event, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, can_be_deleted=False, context=None):
        return super(calendar_event, self).unlink(cr, uid, ids, can_be_deleted=can_be_deleted, context=context)

    _columns = {
        'oe_update_date': fields.datetime('Odoo Update Date'),
    }


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
