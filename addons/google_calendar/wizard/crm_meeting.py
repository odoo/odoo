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

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from datetime import datetime
from dateutil import parser


import pytz
import urllib
import urllib2
import json
import werkzeug.utils

class crm_meeting_synchronize(osv.osv_memory):
    _name = 'crm.meeting.synchronize'


    def synchronize_events(self, cr, uid, ids, context=None):
        gc_obj = self.pool.get('google.calendar')
                
        self.create_new_events(cr, uid, context=context)
        #self.bind_recurring_events_to_google(cr, uid, context)
        #self.update_events(cr, uid, access_token, context)
        return True
#     
#     def generate_data(self, cr, uid, event, context):
#         if event.allday:
#             start_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T').split('T')[0]
#             end_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T').split('T')[0]
#             type = 'date'
#         else:
#             start_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T')
#             end_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.date_deadline, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T')
#             type = 'dateTime'
#         attendee_list = []
#         for attendee in event.attendee_ids:
#             attendee_list.append({
#                 'email':attendee.email,
#                 'displayName':attendee.partner_id.name,
#                 'responseStatus':google_state_mapping.get(attendee.state, 'needsAction'),
#             })
#         data = {
#             "summary": event.name or '',
#             "description": event.description or '',
#             "start":{
#                  type:start_date,
#                  'timeZone':context.get('tz')
#              },
#             "end":{
#                  type:end_date,
#                  'timeZone':context.get('tz')
#              },
#             "attendees":attendee_list,
#             "colorId":4,
#             "location":event.location or '',
#             "visibility":event['class'] or 'public',
#         }
#         if event.rrule:
#             data["recurrence"]=["RRULE:"+event.rrule]
#         return data
#     
    def create_new_events(self, cr, uid, context):
        gc_pool = self.pool.get('google.calendar')
        
        crm_meeting = self.pool['crm.meeting']
        user_obj = self.pool['res.users']
        
        print "TO CHECK RESULT HERE >>>>>>>>>>>>>>>>>>>>"
        
        
        
        
        context_norecurrent = context.copy()
        context_norecurrent['virtual_id'] = False
        
        new_events_ids = crm_meeting.search(cr, uid,[('partner_ids', 'in', user_obj.browse(cr,uid,uid,context=context).partner_id.id),('google_internal_event_id', '=', False)], context=context_norecurrent)
        #new_events_ids = [str(i).split('-')[0] for i in new_events_ids]
        #new_events_ids = base_calendar_id2real_id(new_events_ids,False); #[str(i).split('-')[0] for i in new_events_ids]
        
        print 'Events ids [new_events_ids] : ', new_events_ids
        
        for event in crm_meeting.browse(cr, uid, list(set(new_events_ids)), context):
            response = gc_pool.create_event(cr,uid,event,context=context)
            update_date = datetime.strptime(response['updated'],"%Y-%m-%dT%H:%M:%S.%fz")
            crm_meeting.write(cr, uid, event.id, {'google_internal_event_id': response['id'], 'oe_update_date':update_date})
            
            #Check that response OK and return according to that
        
        return True
#     
#     def bind_recurring_events_to_google(self, cr, uid,  context):
#         crm_meeting = self.pool['crm.meeting']
#         new_events_ids = crm_meeting.search(cr, uid,[('user_id', '=', uid),('google_internal_event_id', '=', False),('recurrent_id', '>', 0)], context)
#         new_events_ids = base_calendar_id2real_id(new_events_ids,False); #[str(i).split('-')[0] for i in new_events_ids]
#         
#         for event in crm_meeting.browse(cr, uid, list(set(new_events_ids)), context):
#             source_record = crm_meeting.read(cr, uid ,event.recurrent_id,['allday', 'google_internal_event_id'],context)
#             new_google_internal_event_id = False
#             if event.recurrent_id_date and source_record.get('allday') and source_record.get('google_internal_event_id'):
#                 new_google_internal_event_id = source_record.get('google_internal_event_id') +'_'+ event.recurrent_id_date.split(' ')[0].replace('-','') + 'Z'
#             elif event.recurrent_id_date and source_record.get('google_internal_event_id'):
#                 new_google_internal_event_id = source_record.get('google_internal_event_id') +'_'+ event.recurrent_id_date.replace('-','').replace(' ','T').replace(':','') + 'Z'
#             if new_google_internal_event_id:
#                 crm_meeting.write(cr, uid, [event.id], {'google_internal_event_id': new_google_internal_event_id})

    def get_event_dict(self,access_token, nextPageToken):
        request_url = "https://www.googleapis.com/calendar/v3/calendars/%s/events?fields=%s&access_token=%s" % ('primary',urllib.quote('items,nextPageToken') ,access_token)
        if nextPageToken:
            request_url += "&pageToken=%s" %(nextPageToken)
        try:
            req = urllib2.Request(request_url)
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError,e:
            error_message = e.read()
            print error_message
        content = json.loads(content)
        google_events_dict = {}
        for google_event in content['items']:
            if google_event.get('updated',False):
                google_events_dict[google_event['id']] = google_event
        if content.get('nextPageToken', False):
            google_events_dict.update(self.get_event_dict(access_token,content['nextPageToken']))
        return google_events_dict
    
    def update_events(self, cr, uid, access_token, context):
        crm_meeting = self.pool['crm.meeting']
        google_event_dict = self.get_event_dict(access_token, False)
        updated_events_ids = crm_meeting.search(cr, uid,[('partner_ids', 'in', user_obj.browse(cr,uid,uid,context=context)),('google_internal_event_id', '!=', False),('oe_update_date','!=', False)], context)
        for event in crm_meeting.browse(cr, uid, list(set(updated_events_ids)), context):
            if event.google_internal_event_id in google_event_dict:
                self.check_and_sync(cr, uid, access_token, event, google_event_dict[event.google_internal_event_id], context)
                del google_event_dict[event.google_internal_event_id]
            else:
                request_url = "https://www.googleapis.com/calendar/v3/calendars/%s/events/%s?access_token=%s" % ('primary', event.google_internal_event_id, access_token)
                content = {}
                try:
                    req = urllib2.Request(request_url)
                    content = urllib2.urlopen(req).read()
                except urllib2.HTTPError,e:
                    error_message = e.read()
                    print error_message
                    if e.code == 404:
                        print "Need DELETE"
                if content:
                    content = json.loads(content)
                    self.check_and_sync(cr, uid, access_token, event, content, context)
        for new_google_event in google_event_dict.values():
            if new_google_event.get('recurringEventId',False):
                reccurent_event = crm_meeting.search(cr, uid, [('google_internal_event_id', '=', new_google_event['recurringEventId'])])
                new_google_event_id = new_google_event['id'].split('_')[1].replace('T','')[:-1]
                for event_id in reccurent_event:
                    if isinstance(event_id, str) and len(event_id.split('-'))>1 and event_id.split('-')[1] == new_google_event_id:
                        reccurnt_event_id = int(event_id.split('-')[0].strip())
                        parent_event = crm_meeting.read(cr,uid, reccurnt_event_id, [], context)
                        parent_event['id'] = event_id
                        #reccurent update from google
                        self.update_from_google(cr, uid, parent_event, new_google_event, "copy", context)
            else:
                #new event from google
                self.update_from_google(cr, uid, False, new_google_event, "create", context)
#                 del google_events_dict[new_google_event['id']]
        
    def check_and_sync(self, cr, uid, access_token, oe_event, google_event, context):
        if datetime.strptime(oe_event.oe_update_date,"%Y-%m-%d %H:%M:%S.%f") > datetime.strptime(google_event['updated'],"%Y-%m-%dT%H:%M:%S.%fz"):
            #update to google 
            self.update_to_google(cr, uid, access_token, oe_event, google_event, context)
        elif datetime.strptime(oe_event.oe_update_date,"%Y-%m-%d %H:%M:%S.%f") < datetime.strptime(google_event['updated'],"%Y-%m-%dT%H:%M:%S.%fz"):
            #update from google
            self.update_from_google(cr, uid, oe_event, google_event, 'write', context)
        pass
    
    def update_to_google(self, cr, uid, access_token, oe_event, google_event, context):
        crm_meeting = self.pool['crm.meeting']
        request_url = "https://www.googleapis.com/calendar/v3/calendars/%s/events/%s?fields=%s" % ('primary', google_event['id'], urllib.quote('id,updated'))
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data = self.generate_data(cr,uid ,oe_event, context)
        data['sequence'] = google_event.get('sequence', 0)
        data_json = json.dumps(data)
        try:
            req = urllib2.Request(request_url, data_json, headers)
            req.get_method = lambda: 'PATCH'
            content = urllib2.urlopen(req).read()
        except urllib2.HTTPError,e:
            error_message = json.loads(e.read())
            
        content = json.loads(content)
        update_date = datetime.strptime(content['updated'],"%Y-%m-%dT%H:%M:%S.%fz")
        crm_meeting.write(cr, uid, [oe_event.id], {'oe_update_date':update_date})
    
    def update_from_google(self, cr, uid, event, single_event_dict, type, context):
        crm_meeting = self.pool['crm.meeting']
        res_partner_obj = self.pool['res.partner']
        calendar_attendee_obj = self.pool['calendar.attendee']
        attendee_record= [] 
        result = {}
        if single_event_dict.get('attendees',False):
            for google_attendee in single_event_dict['attendees']:
                if type == "write":
                    for oe_attendee in event['attendee_ids']:
                        if calendar_attendee_obj.browse(cr, uid ,oe_attendee,context=context).email == google_attendee['email']:
                            calendar_attendee_obj.write(cr, uid,[oe_attendee] ,{'state' : oe_state_mapping[google_attendee['responseStatus']]})
                            google_attendee['found'] = True
                if google_attendee.get('found',False):
                    continue
                attendee_id = res_partner_obj.search(cr, uid,[('email', '=', google_attendee['email'])], context=context)
                if not attendee_id:
                    attendee_id = [res_partner_obj.create(cr, uid,{'email': google_attendee['email'], 'name': google_attendee.get("displayName",False) or google_attendee['email'] }, context=context)]
                attendee = res_partner_obj.read(cr, uid, attendee_id[0], ['email'], context=context)
                attendee['partner_id'] = attendee.pop('id')
                attendee['state'] = oe_state_mapping[google_attendee['responseStatus']]
                attendee_record.append((0, 0, attendee))
        if single_event_dict['start'].get('dateTime',False) and single_event_dict['end'].get('dateTime',False):
            UTC = pytz.timezone('UTC')
            date = parser.parse(single_event_dict['start']['dateTime'])
            date_deadline = parser.parse(single_event_dict['end']['dateTime'])
            delta = date_deadline.astimezone(UTC) - date.astimezone(UTC)
            result['duration'] = (delta.seconds / 60) / 60.0 + delta.days *24
            date = str(date.astimezone(UTC))[:-6]
            date_deadline = str(date_deadline.astimezone(UTC))[:-6]
            allday = False
        else:
            date = single_event_dict['start']['date'] + ' 12:00:00'
            date_deadline = single_event_dict['start']['date'] + ' 12:00:00'
            allday = True
        update_date = datetime.strptime(single_event_dict['updated'],"%Y-%m-%dT%H:%M:%S.%fz")
        result.update({
            'attendee_ids': attendee_record,
            'date': date,
            'date_deadline': date_deadline,
            'allday': allday,
            'name': single_event_dict.get('summary','Event'),
            'description': single_event_dict.get('description',''),
            'location':single_event_dict.get('location',''),
            'class':single_event_dict.get('visibility','public'),
            'oe_update_date':update_date,
            'google_internal_event_id': single_event_dict.get('id',''),
        })
        if single_event_dict.get("recurrence",False):
            rrule = [rule for rule in single_event_dict["recurrence"] if rule.startswith("RRULE:")][0][6:]
            result['rrule']=rrule
        if type == "write":
            crm_meeting.write(cr, uid, event['id'], result, context=context)
        elif type == "copy":
            result['write_type'] = "copy"
            crm_meeting.write(cr, uid, event['id'], result, context=context)
        elif type == "create":
            crm_meeting.create(cr, uid, result, context=context)