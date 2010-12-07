# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from base_calendar import base_calendar
from caldav import calendar
from datetime import datetime
import re

class crm_meeting(osv.osv):
    _inherit = 'crm.meeting'

    def export_cal(self, cr, uid, ids, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of CRM Meeting’s IDs
            @param context: A standard dictionary for contextual values
        """
        if not context:
            context = {}
        ids = map(lambda x: base_calendar.base_calendar_id2real_id(x), ids)
        event_data = self.read(cr, uid, ids, context=context)
        event_obj = self.pool.get('basic.calendar.event')
        context.update({'model': self._name})
        ical = event_obj.export_cal(cr, uid, event_data, context=context)
        return ical.serialize()


    def import_cal(self, cr, uid, data, data_id=None, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param data: Get Data of CRM Meetings
            @param data_id: calendar's Id
            @param context: A standard dictionary for contextual values
        """
        if not context:
            context = {}
        event_obj = self.pool.get('basic.calendar.event')
        vals = event_obj.import_cal(cr, uid, data, context=context)
        return self.check_import(cr, uid, vals, context=context)

    def check_import(self, cr, uid, vals, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param vals: Get Values
            @param context: A standard dictionary for contextual values
        """
        if not context:
            context = {}
        ids = []
        model_obj = self.pool.get(context.get('model'))
        recur_pool = {}
        try:
            for val in vals:
                # Compute value of duration
                if val.get('date_deadline', False) and 'duration' not in val:
                    start = datetime.strptime(val['date'], '%Y-%m-%d %H:%M:%S')
                    end = datetime.strptime(val['date_deadline'], '%Y-%m-%d %H:%M:%S')
                    diff = end - start
                    val['duration'] = (diff.seconds/float(86400) + diff.days) * 24
                exists, r_id = calendar.uid2openobjectid(cr, val['id'], context.get('model'), \
                                                                 val.get('recurrent_id'))
                if val.has_key('create_date'):
                    val.pop('create_date')
                u_id = val.get('id', None)
                val.pop('id')
                if exists and r_id:
                    val.update({'recurrent_uid': exists})
                    model_obj.write(cr, uid, [r_id], val)
                    ids.append(r_id)
                    
                elif exists:
                    model_obj.write(cr, uid, [exists], val)
                    ids.append(exists)
                else:
                    if u_id in recur_pool and val.get('recurrent_id'):
                        val.update({'recurrent_uid': recur_pool[u_id]})
                        revent_id = model_obj.create(cr, uid, val)
                        ids.append(revent_id)
                    else:
                        __rege = re.compile(r'OpenObject-([\w|\.]+)_([0-9]+)@(\w+)$')
                        wematch = __rege.match(u_id.encode('utf8'))
                        if wematch:
                            model, recur_id, dbname = wematch.groups()
                            val.update({'recurrent_uid': recur_id})
                        event_id = model_obj.create(cr, uid, val)
                        recur_pool[u_id] = event_id
                        ids.append(event_id)
        except Exception:
            raise
        return ids
    
crm_meeting()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

