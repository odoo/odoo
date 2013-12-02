##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP SA (<http://www.openerp.com>).
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

import simplejson
import re
import urllib
import urllib2


from openerp import tools
from openerp.tools.translate import _

from openerp.addons.web.http import request
import werkzeug.utils

from datetime import datetime, timedelta, date

from openerp.osv import fields, osv
from openerp.osv import osv


google_state_mapping = {
    'needs-action':'needsAction',
    'declined': 'declined',
    'tentative':'tentative',
    'accepted':'accepted',
    'delegated':'declined',
}
oe_state_mapping = {
    'needsAction':'needs-action',
    'declined': 'declined',
    'tentative':'tentative',
    'accepted':'accepted',
}

class google_calendar(osv.osv):
    _name = 'google.calendar'
    
    STR_SERVICE = 'calendar'
    
    def authorize_google_uri(self,cr,uid,from_url='http://www.openerp.com',context=None):
        url = self.pool.get('google.service')._get_authorize_uri(cr,uid,from_url,self.STR_SERVICE,scope=self.get_calendar_scope(),context=context)
        return url        
        
    def set_all_tokens(self,cr,uid,authorization_code,context=None):
        gs_pool = self.pool.get('google.service')
        all_token = gs_pool._get_google_token_json(cr, uid, authorization_code,self.STR_SERVICE,context=context)
                
        vals = {}
        vals['google_%s_rtoken' % self.STR_SERVICE] = all_token.get('refresh_token')
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in')) #NEED A CALCUL
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')           
        self.pool.get('res.users').write(cr,uid,uid,vals,context=context)
    
    def set_primary_id(self,cr,uid,context=None):
        gs_pool = self.pool.get('google.service')

        params = {
            'fields': 'id',
            'access_token': self.get_token(cr, uid, context=context)
        }       
        
        cal = gs_pool._do_request(cr, uid, "/calendar/v3/calendars/primary/", params, type='GET', context=context)
        
        if cal.get('id',False):
            vals = {}
            vals['google_calendar_id']= cal.get('id')
            self.pool.get('res.users').write(cr,uid,uid,vals,context=context)
            return True
        else:
            return False        
    
    def generate_data(self, cr, uid, event, context=None):
        if event.allday:
            start_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date, tools.DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=0), context=context).isoformat('T').split('T')[0]
            end_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date, tools.DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=24), context=context).isoformat('T').split('T')[0]
            type = 'date'
        else:
            start_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T')
            end_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date_deadline, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T')
            type = 'dateTime'
        attendee_list = []
        
        for attendee in event.attendee_ids:
            attendee_list.append({
                'email':attendee.email or 'NoEmail@mail.com',
                'displayName':attendee.partner_id.name,
                'responseStatus':google_state_mapping.get(attendee.state, 'needsAction'),
            })
        data = {
            "summary": event.name or '',
            "description": event.description or '',
            "start":{
                 type:start_date,
                 #'timeZone':context.get('tz') or 'UTC'
             },
            "end":{
                 type:end_date,                 
                 #'timeZone':context.get('tz') or 'UTC'
             },
            "attendees":attendee_list,
            "location":event.location or '',
            "visibility":event['class'] or 'public',
        }
        if event.recurrency and event.rrule:
            data["recurrence"]= []
            if event.exdate:
                data["recurrence"].append("EXDATE:"+event.exdate)    
            
            data["recurrence"]+=["RRULE:"+event.rrule]
            
        
        #if not recurrency and event.recurrent_id and event.recurrent_id != 0: ###" IMMUTABLE
        #    data["recurringEventId"] = event.recurrent_id
            
        print data    
        return data
    
    def create_event(self, cr, uid,event, context=None):
        gs_pool = self.pool.get('google.service')
        
        print "CONTEXT : ",context
        data = self.generate_data(cr, uid,event, context=context)
        
        
        url = "/calendar/v3/calendars/%s/events?fields=%s&access_token=%s" % ('primary',urllib.quote('id,updated'),self.get_token(cr,uid,context))
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)
        
        response = gs_pool._do_request(cr, uid, url, data_json, headers, type='POST', context=context)
        #TODO Check response result
        
        return response
        
    def get_token(self,cr,uid,context=None):
        current_user = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        if datetime.strptime(current_user.google_calendar_token_validity.split('.')[0], "%Y-%m-%d %H:%M:%S") < datetime.now() - timedelta(minutes=5):
            print "NEED TO RENEW TOKEN",current_user.google_calendar_token_validity , "<", datetime.now() - timedelta(minutes=5)
            self.do_refresh_token(cr,uid,context=context)
            current_user.refresh()
        else:
            print "KEEP OLD TOKEN",current_user.google_calendar_token_validity , "<", datetime.now() - timedelta(minutes=5)
        return current_user.google_calendar_token

    def do_refresh_token(self,cr,uid,context=None):
        current_user = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        gs_pool = self.pool.get('google.service')
        
        refresh = current_user.google_calendar_rtoken
        all_token = gs_pool._refresh_google_token_json(cr, uid, current_user.google_calendar_rtoken,self.STR_SERVICE,context=context)
                
        vals = {}
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in')) 
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')  
    
        self.pool.get('res.users').write(cr,uid,uid,vals,context=context)
        

    def get_refresh_token(self,cr,uid,context=None):
        current_user = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        return current_user.google_calendar_rtoken
            
    def get_calendar_scope(self,RO=False):
        readonly = RO and '.readonly' or '' 
        return 'https://www.googleapis.com/auth/calendar%s' % (readonly)        

class res_users(osv.osv): 
    _inherit = 'res.users'
    
    _columns = {
        'google_calendar_id': fields.char('Primary Calendar ID'),
        'google_calendar_rtoken': fields.char('Refresh Token'),
        'google_calendar_token': fields.char('User token'), 
        'google_calendar_token_validity': fields.datetime('Token Validity'),       
     }
        
    def get_cal_token_info(self, cr, uid, partner_id=False, context=None):
        if partner_id:
            user = self.pool.get('res.partner').browse(cr,uid,partner_id,context=context).user_id
        else:
            user = self.pool.get('res.users').browse(cr,uid,uid,context=context)
        
        return dict(authcode=user.google_cal_authcode, token=user.google_cal_token, validity=user.google_cal_token_validity,)
    
    def update_cal_token(self,cr,uid,jsontoken,context=None):
        print jsontoken
        import ipdb; ipdb.set_trace();
        self.write(cr,uid,uid,{'xxx' : datetime.now() } ,context=context)
        return "OK"             



class crm_meeting(osv.osv):
    _inherit = "crm.meeting"
    
    def write(self, cr, uid, ids, vals, context=None):
        sync_fields = set(['name', 'description', 'date', 'date_closed', 'date_deadline', 'attendee_ids', 'location', 'class'])
        if (set(vals.keys()) & sync_fields) and 'oe_update_date' not in vals.keys():
            vals['oe_update_date'] = datetime.now()
        return super(crm_meeting, self).write(cr, uid, ids, vals, context=context)
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default['attendee_ids'] = False
        if default.get('write_type', False):
            del default['write_type']
        elif default.get('recurrent_id', False):
            default['oe_update_date'] = datetime.now()
            default['google_internal_event_id'] = False
        else:
            default['google_internal_event_id'] = False
            default['oe_update_date'] = False
        return super(crm_meeting, self).copy(cr, uid, id, default, context)
    
    _columns = {
        'google_internal_event_id': fields.char('Google Calendar Event Id', size=124),
        'oe_update_date': fields.datetime('OpenERP Update Date'),
    }
    
# If attendees are updated, we need to specify that next synchro need an action    
class calendar_attendee(osv.osv):
    _inherit = 'calendar.attendee'
    
    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, list):
            cr.execute("SELECT crmmeeting_id FROM crmmeeting_attendee_rel WHERE attendee_id = %s"%(ids[0]))
        else:
            cr.execute("SELECT crmmeeting_id FROM crmmeeting_attendee_rel WHERE attendee_id = %s"%(ids))
        event_id = cr.fetchone()[0]
        if event_id:
            self.pool.get('crm.meeting').write(cr, uid, event_id, {'oe_update_date':datetime.now()})
        return super(calendar_attendee, self).write(cr, uid, ids, vals, context=context)

