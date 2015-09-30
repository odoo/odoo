# -*- coding: utf-8 -*-
from datetime import datetime

from openerp.osv import osv, fields

class calendar_event(osv.Model):
    _inherit = "calendar.event"

    def get_fields_need_update_google(self, cr, uid, context=None):
        return ['name', 'description', 'allday', 'start', 'date_end', 'stop',
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