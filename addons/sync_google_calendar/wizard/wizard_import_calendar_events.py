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

from osv import fields,osv
from tools.translate import _
import tools

import time
import datetime
import dateutil
from dateutil.tz import *
from dateutil.parser import *

import urllib

try:
    import gdata
    import gdata.calendar.service
    import gdata.calendar
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

def _get_tinydates(self, stime, etime):
    stime = dateutil.parser.parse(stime)
    etime = dateutil.parser.parse(etime)
    try:
        au_dt = au_tz.normalize(stime.astimezone(au_tz))
        timestring = datetime.datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
        au_dt = au_tz.normalize(etime.astimezone(au_tz))
        timestring_end = datetime.datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
    except:
        timestring = datetime.datetime(*stime.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
        timestring_end = datetime.datetime(*etime.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
    return (timestring, timestring_end)

class google_login(osv.osv_memory):
    _inherit = 'google.login'
    _name = 'google.login'

    def _get_next_action(self, cr, uid, context=None):
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'sync_google_calendar', 'view_synchronize_google_calendar_import_form')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
        value = {
            'name': _('Import Events'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'synchronize.google.calendar',
            'view_id': False,
            'context': context,
            'views': [(view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return value

google_login()

class synchronize_google_calendar_events(osv.osv_memory):
    _name = 'synchronize.google.calendar'
    
    def _get_calendars(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        google = self.pool.get('google.login')
        res = []
        gd_client = google.google_login(cr, uid, user_obj.gmail_user, user_obj.gmail_password, type='calendar')
        calendars = gd_client.GetAllCalendarsFeed()
        for cal in calendars.entry:
            res.append((cal.id.text, cal.title.text))
        res.append(('default','Default Calendar'))
        return res
    
    _columns = {
        'calendar_name': fields.selection(_get_calendars, "Calendar Name", size=32),
    }
    
    _defaults = {
        'calendar_name': 'default',
    }
    
    def import_calendar_events(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids, context=context)[0]
        if not ids:
            return { 'type': 'ir.actions.act_window_close' }

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        meeting_obj = self.pool.get('crm.meeting')
        model_obj = self.pool.get('ir.model.data')
        gmail_user = user_obj.gmail_user
        gamil_pwd = user_obj.gmail_password
        
        google = self.pool.get('google.login')
        gd_client = google.google_login(cr, uid, gmail_user, gamil_pwd, type='calendar')

        if not gmail_user or not gamil_pwd:
            raise osv.except_osv(_('Error'), _("Please specify the user and password !"))
        
        if obj.calendar_name != 'default':
            events_query = gdata.calendar.service.CalendarEventQuery(user=urllib.unquote(obj.calendar_name.split('/')[~0]))
            events_query.start_index = 1
            events_query.max_results = 1000
            event_feed = gd_client.GetCalendarEventFeed(events_query.ToUri())
        else:
            event_feed = gd_client.GetCalendarEventFeed()

        meeting_ids = []
        for feed in event_feed.entry:
            google_id = feed.id.text
            model_data = {
                'name': google_id,
                'model': 'crm.meeting',
                'module': 'sync_google_calendar',
            }
            vals = {
                'name': feed.title.text,
                'description': feed.summary
            }
            timestring, timestring_end = _get_tinydates(self, feed.when[0].start_time, feed.when[0].end_time)
            vals.update({'date': timestring, 'date_deadline': timestring_end})
            data_ids = model_obj.search(cr, uid, [('model','=','crm.meeting'), ('name','=',google_id)])
            if data_ids:
                meeting_ids.append(model_obj.browse(cr, uid, data_ids[0], context=context).res_id)
            else:
                res_id = meeting_obj.create(cr, uid, vals)
                meeting_ids.append(res_id)
                model_data.update({'res_id': res_id})
                model_obj.create(cr, uid, model_data, context=context)
        
        return {
            'name': _('Meetings'),
            'domain': "[('id','in', ["+','.join(map(str,meeting_ids))+"])]",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.meeting',
            'context': context,
            'views': [(False, 'tree'),(False, 'form')],
            'type': 'ir.actions.act_window',
        }
    
synchronize_google_calendar_events()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

