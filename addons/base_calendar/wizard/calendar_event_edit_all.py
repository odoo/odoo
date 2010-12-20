# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from osv import fields

class calendar_event_edit_all(osv.osv_memory):

    def _default_values(self, cr, uid, context=None):
        """ Get Default value for Start Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @Return: Get Default value for Start Date
        """
        context_id = context and context.get('active_id', False) or False
        if context_id:
            if context.get('date'):
                return context.get('date')
            else:
                model = context.get('model', False)
                model_obj = self.pool.get(model)
                event = model_obj.read(cr, uid, context_id, ['name', 'location', 'alarm_id'])
                return event['date']

    def _default_deadline(self, cr, uid, context=None):
        """ Get Default value for End Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param context: A standard dictionary for contextual values
        @return: Get Default value for End Date
        """

        context_id = context and context.get('active_id', False) or False
        if context_id:
            if context.get('date_deadline'):
                return context.get('date_deadline')
            else:
                model = context.get('model', False)
                model_obj = self.pool.get(model)
                event = model_obj.read(cr, uid, context_id, ['name', 'location', 'alarm_id'])
                return event['date_deadline']

    def modify_this(self, cr, uid, ids, context=None):
        """
        Modify All event for Crm Meeting.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar event edit all’s IDs
        @return: dictionary {}
        """
        if context is None:
            context = {}

        context_id = context and context.get('active_id', False) or False
        if context_id:
            for datas in self.read(cr, uid, ids):
                model = context.get('model', False)
                model_obj = self.pool.get(model)
                model_obj.modify_all(cr, uid, [context_id], datas, context=context)
                return {}

    _name = "calendar.event.edit.all"
    _description = "Calendar Edit all event"
    _columns = {
        'name': fields.char('Title', size=64, required=True),
        'date': fields.datetime('Start Date', required=True),
        'date_deadline': fields.datetime('End Date', required=True),
        'location': fields.char('Location', size=124),
        'alarm_id': fields.many2one('res.alarm', 'Reminder'),
    }
    _defaults = {
        'date': _default_values,
        'date_deadline': _default_deadline
    }
calendar_event_edit_all()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
