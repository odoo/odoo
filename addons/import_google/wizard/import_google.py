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

import re
import urllib
import dateutil
import pytz
from dateutil import *
from pytz import timezone
from datetime import datetime
import time
from osv import *
from tools.translate import _

try:
    import gdata
    import gdata.contacts.service
    import gdata.calendar.service
    import gdata.contacts
    import gdata.calendar
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))
from import_base.import_framework import *
from import_base.mapper import *

class google_import(import_framework):

    gd_client = False
    calendars = False
    contact = False
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    TABLE_CONTACT = 'Contact'
    TABLE_ADDRESS ='Address'
    TABLE_EVENT = 'Events'

    def initialize(self):
        google = self.obj.pool.get('google.login')
        self.gd_client = google.google_login(self.context.get('user'),
                                       self.context.get('password'),
                                        self.context.get('instance'))

        if self.context.get('instance') and self.context.get('instance') == 'contact':
            self.contact = self.context.get('contact')
        if self.context.get('instance') and self.context.get('instance') == 'calendar':
            self.calendars = self.context.get('calendars')

    def get_mapping(self):
        return {
            self.TABLE_EVENT: self.get_event_mapping(),
            self.TABLE_CONTACT: self.get_contact_mapping(),
            self.TABLE_ADDRESS: self.get_address_mapping(),
        }

    def get_data(self, table):
        data_fetching_function = {
              self.TABLE_CONTACT: self.get_contact,
              self.TABLE_ADDRESS: self.get_contact,
              self.TABLE_EVENT: self.get_events,
        }

        return data_fetching_function.get(table)()


    def _get_tinydates(self, stime, etime, au_tz):
        stime = dateutil.parser.parse(stime)
        etime = dateutil.parser.parse(etime)
        try:
            au_dt = au_tz.normalize(stime.replace(tzinfo=pytz.utc).astimezone(au_tz))
            timestring = datetime.datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
            au_dt = au_tz.normalize(etime.replace(tzinfo=pytz.utc).astimezone(au_tz))
            timestring_end = datetime.datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
        except:
            timestring = datetime.datetime(*stime.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
            timestring_end = datetime.datetime(*etime.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
        return (timestring, timestring_end)

    def _get_rules(self, datas):
        new_val = {}
        if  datas['FREQ'] == 'WEEKLY' and datas.get('BYDAY'):
            for day in datas['BYDAY'].split(','):
                new_val[day.lower()] = True
            datas.pop('BYDAY')

        if datas.get('UNTIL'):
            until = parser.parse(''.join((re.compile('\d')).findall(datas.get('UNTIL'))))
            new_val['end_date'] = until.strftime('%Y-%m-%d')
            new_val['end_type'] = 'end_date'
            datas.pop('UNTIL')

        if datas.get('COUNT'):
            new_val['count'] = datas.get('COUNT')
            new_val['end_type'] = 'count'
            datas.pop('COUNT')

        if datas.get('INTERVAL'):
            new_val['interval'] = datas.get('INTERVAL')
        else:
            new_val['interval'] = 1

        if datas.get('BYMONTHDAY'):
            new_val['day'] = datas.get('BYMONTHDAY')
            datas.pop('BYMONTHDAY')
            new_val['select1'] = 'date'

        if datas.get('BYDAY'):
            d = datas.get('BYDAY')
            if '-' in d:
                new_val['byday'] = d[:2]
                new_val['week_list'] = d[2:4].upper()
            else:
                new_val['byday'] = d[:1]
                new_val['week_list'] = d[1:3].upper()
            new_val['select1'] = 'day'

        if datas.get('BYMONTH'):
            new_val['month_list'] = datas.get('BYMONTH')
            datas.pop('bymonth')
        return new_val


    def _get_repeat_status(self, str_google):
        rrule = str_google[str_google.find('FREQ'):str_google.find('\nBEGIN')]
        status = {}
        for rule in rrule.split(';'):
            status[rule.split('=')[0]] = rule.split('=')[-1:] and rule.split('=')[-1:][0] or ''
        rules = self._get_rules(status)
        if status.get('FREQ') == 'WEEKLY':
            status.update({'rrule_type': 'weekly'})
            status.pop('FREQ')
        elif status.get('FREQ') == 'DAILY':
            status.update({'rrule_type': 'daily'})
            status.pop('FREQ')
        elif status.get('FREQ') == 'MONTHLY':
            status.update({'rrule_type': 'monthly'})
            status.pop('FREQ')
        elif status.get('FREQ') == 'YEARLY':
            status.update({'rrule_type': 'yearly'})
            status.pop('FREQ')
        status.update(rules)
        return status


    def _get_repeat_dates(self, x):
        if len(x) > 4:
            if x[3].startswith('BY'):
                zone_time = x[4].split('+')[-1:][0].split(':')[0][:4]
            else:
                zone_time = x[3].split('+')[-1:][0].split(':')[0][:4]
        else:
            zone_time = x[2].split('+')[-1:][0].split(':')[0][:4]
        tz_format = zone_time[:2]+':'+zone_time[2:]
        repeat_start = x[1].split('\n')[0].split(':')[1]
        repeat_end = x[2].split('\n')[0].split(':')[1]
        o = repeat_start.split('T')
        repeat_start = str(o[0][:4]) + '-' + str(o[0][4:6]) + '-' + str(o[0][6:8])
        if len(o) == 2:
            repeat_start += ' ' + str(o[1][:2]) + ':' + str(o[1][2:4]) + ':' + str(o[1][4:6])
        else:
            repeat_start += ' ' + '00' + ':' + '00' + ':' + '00'
        p = repeat_end.split('T')
        repeat_end = str(p[0][:4]) + '-' + str(p[0][4:6]) + '-' + str(p[0][6:8])
        if len(p) == 2:
            repeat_end += ' ' + str(p[1][:2]) + ':' + str(p[1][2:4]) + ':' + str(p[1][4:6])
        else:
            repeat_end += ' ' + '00' + ':' + '00' + ':' + '00'
        return (repeat_start, repeat_end, tz_format)

    def get_events(self):
        if 'tz' in self.context and self.context['tz']:
            time_zone = self.context['tz']
        else:
            time_zone = tools.get_server_timezone()
        au_tz = timezone(time_zone)
        event_vals = []
        for cal in self.calendars:
            events_query = gdata.calendar.service.CalendarEventQuery(user=urllib.unquote(cal.split('/')[~0]))
            events_query.start_index = 1
            events_query.max_results = 1000
            event_feed = self.gd_client.GetCalendarEventFeed(events_query.ToUri())
            for feed in event_feed.entry:
                event = {
                    'recurrency': False,
                    'end_date' : False,
                    'end_type' : False,
                    'byday': 0,
                    'count' : 0,
                    'interval': 1,
                    'day': False,
                    'select1': False,
                    'week_list': "",
                    'month_list': False,
                    'rrule_type': False,
                }

                timestring = timestring_end = datetime.datetime.now().strftime(self.DATETIME_FORMAT)
                if feed.when:
                    timestring, timestring_end = self._get_tinydates(feed.when[0].start_time, feed.when[0].end_time, au_tz)
                else:
                    x = feed.recurrence.text.split(';')
                    repeat_status = self._get_repeat_status(feed.recurrence.text)
                    repeat_start, repeat_end, zone_time = self._get_repeat_dates(x)
                    timestring = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(repeat_start, "%Y-%m-%d %H:%M:%S"))
                    timestring_end = time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(repeat_end, "%Y-%m-%d %H:%M:%S"))
                    if repeat_status:
                        repeat_status.update({'recurrency': True})
                        event.update(repeat_status)

                event.update({'id' : feed.id.text,
                              'DateStart': timestring,
                              'DateEnd': timestring_end,
                              'Category':event_feed.title.text,
                              'Name': feed.title.text or 'No title',
                              'Description': feed.content.text,
                              })
                event_vals.append(event)
        return event_vals


    def get_event_category(self, val, name):
        nameid = 'event_category_' + name
        fields = ['name']
        data = [name]
        return self.import_object(fields, data, 'crm.meeting.type', "crm_meeting_type", nameid, [('name', 'ilike', name)])

    def get_rec(self, val):
        if val.get("recurrency"):
            return "1"
        return "0"

    def get_event_mapping(self):
        return {
            'model': 'crm.meeting',
            'map': {
                    'id': 'id',
                    'name': 'Name',
                    'description': 'Description',
                    'email_from': 'Email',
                    'date': 'DateStart',
                    'date_deadline': 'DateEnd',
                    'categ_id/id': call(self.get_event_category, value('Category')),
                    'recurrency': self.get_rec,
                    'end_date' : 'end_date',
                    'end_type' : 'end_type',
                    'byday':'byday',
                    'count' : 'count',
                    'interval': 'interval',
                    'day': 'day',
                    'select1': 'date',
                    'week_list': 'week_list',
                    'month_list':'month_list',
                    'rrule_type': 'rrule_type',
                }
        }


    def get_contact(self):
        table = self.context.get('table')[0]
        datas = []
        if self.context.get('group_name'):
            query = gdata.contacts.service.ContactsQuery()
            query.group = self.context.get('group_name')
            self.contact = self.gd_client.GetContactsFeed(query.ToUri())
        else:
            self.contact = self.gd_client.GetContactsFeed()
        while self.contact:
            for entry in self.contact.entry:
                data = {}
                data['id'] = entry.id.text
                name = tools.ustr(entry.title.text)
                if name == "None":
                    name = entry.email and entry.email[0].address or ''
                data['name'] = name or _('Unknown')
                emails = ','.join(email.address for email in entry.email)
                data['email'] = emails
                if table == 'Contact':
                    data.update({'customer': str(self.context.get('customer')),
                                 'supplier': str(self.context.get('supplier'))})
                if entry.organization:
                    if entry.organization.org_name:
                        data.update({'company': entry.organization.org_name.text})
                    if entry.organization.org_title:
                        data.update ({'function': entry.organization.org_title.text})
                if entry.phone_number:
                    for phone in entry.phone_number:
                        if phone.rel == gdata.contacts.REL_WORK:
                            data['phone'] = phone.text
                        if phone.rel == gdata.contacts.PHONE_MOBILE:
                            data['mobile'] = phone.text
                        if phone.rel == gdata.contacts.PHONE_WORK_FAX:
                            data['fax'] = phone.text
                datas.append(data)
            next = self.contact.GetNextLink()
            self.contact = next and self.gd_client.GetContactsFeed(next.href) or None
        return datas



    def get_contact_mapping(self):
        return {
            'model': 'res.partner',
            #'dependencies': [self.TABLE_ADDRESS],
            'map': {
                'id':'id',
                'name': value('company', fallback='name'),
                'customer': 'customer',
                'supplier': 'supplier',
                'child_ids/id': ref(self.TABLE_ADDRESS, 'id'),
                }
            }

    def get_partner_id(self, val):
        partner_id = False
        company_pool = self.obj.pool.get('res.partner')
        if 'company' in val:
            partner_ids = company_pool.search(self.cr, self.uid, [('name', '=', val.get('company'))])
            return partner_ids and partner_ids[0] or False
        contact = self.xml_id_exist(self.TABLE_CONTACT, val.get('id'))
        if contact:
            partner_id = self.get_mapped_id(self.TABLE_CONTACT, val.get('id'))
        return partner_id

    def get_address_mapping(self):
        return {
            'model': 'res.partner',
            'dependencies': [],
            'map': {
                'id':'id',
                'parent_id/.id': self.get_partner_id,
                'name': 'name',
                'city': 'city',
                'phone': 'phone',
                'mobile': 'mobile',
                'email': 'email',
                'fax': 'fax',
                'function': 'function'
                }

        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
