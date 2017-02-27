# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil import parser
import json
import logging
import operator
import pytz
import urllib2

from odoo import api, fields, models, tools, _
from odoo.tools import exception_to_unicode

_logger = logging.getLogger(__name__)


def status_response(status):
    return int(str(status)[0]) == 2


class Meta(type):
    """ This Meta class allow to define class as a structure, and so instancied variable
        in __init__ to avoid to have side effect alike 'static' variable """
    def __new__(typ, name, parents, attrs):
        methods = dict((k, v) for k, v in attrs.iteritems()
                       if callable(v))
        attrs = dict((k, v) for k, v in attrs.iteritems()
                     if not callable(v))

        def init(self, **kw):
            for key, val in attrs.iteritems():
                setattr(self, key, val)
            for key, val in kw.iteritems():
                assert key in attrs
                setattr(self, key, val)

        methods['__init__'] = init
        methods['__getitem__'] = getattr
        return type.__new__(typ, name, parents, methods)


class Struct(object):
    __metaclass__ = Meta


class OdooEvent(Struct):
    event = False
    found = False
    event_id = False
    isRecurrence = False
    isInstance = False
    update = False
    status = False
    attendee_id = False
    synchro = False


class GmailEvent(Struct):
    event = False
    found = False
    isRecurrence = False
    isInstance = False
    update = False
    status = False


class SyncEvent(object):
    def __init__(self):
        self.OE = OdooEvent()
        self.GG = GmailEvent()
        self.OP = None

    def __getitem__(self, key):
        return getattr(self, key)

    def compute_OP(self, modeFull=True):
        #If event are already in Gmail and in Odoo
        if self.OE.found and self.GG.found:
            is_owner = self.OE.event.env.user.id == self.OE.event.user_id.id
            #If the event has been deleted from one side, we delete on other side !
            if self.OE.status != self.GG.status and is_owner:
                self.OP = Delete((self.OE.status and "OE") or (self.GG.status and "GG"),
                                 'The event has been deleted from one side, we delete on other side !')
            #If event is not deleted !
            elif self.OE.status and (self.GG.status or not is_owner):
                if self.OE.update.split('.')[0] != self.GG.update.split('.')[0]:
                    if self.OE.update < self.GG.update:
                        tmpSrc = 'GG'
                    elif self.OE.update > self.GG.update:
                        tmpSrc = 'OE'
                    assert tmpSrc in ['GG', 'OE']

                    if self[tmpSrc].isRecurrence:
                        if self[tmpSrc].status:
                            self.OP = Update(tmpSrc, 'Only need to update, because i\'m active')
                        else:
                            self.OP = Exclude(tmpSrc, 'Need to Exclude (Me = First event from recurrence) from recurrence')

                    elif self[tmpSrc].isInstance:
                        self.OP = Update(tmpSrc, 'Only need to update, because already an exclu')
                    else:
                        self.OP = Update(tmpSrc, 'Simply Update... I\'m a single event')
                else:
                    if not self.OE.synchro or self.OE.synchro.split('.')[0] < self.OE.update.split('.')[0]:
                        self.OP = Update('OE', 'Event already updated by another user, but not synchro with my google calendar')
                    else:
                        self.OP = NothingToDo("", 'Not update needed')
            else:
                self.OP = NothingToDo("", "Both are already deleted")

        # New in Odoo...  Create on create_events of synchronize function
        elif self.OE.found and not self.GG.found:
            if self.OE.status:
                self.OP = Delete('OE', 'Update or delete from GOOGLE')
            else:
                if not modeFull:
                    self.OP = Delete('GG', 'Deleted from Odoo, need to delete it from Gmail if already created')
                else:
                    self.OP = NothingToDo("", "Already Deleted in gmail and unlinked in Odoo")
        elif self.GG.found and not self.OE.found:
            tmpSrc = 'GG'
            if not self.GG.status and not self.GG.isInstance:
                # don't need to make something... because event has been created and deleted before the synchronization
                self.OP = NothingToDo("", 'Nothing to do... Create and Delete directly')
            else:
                if self.GG.isInstance:
                    if self[tmpSrc].status:
                        self.OP = Exclude(tmpSrc, 'Need to create the new exclu')
                    else:
                        self.OP = Exclude(tmpSrc, 'Need to copy and Exclude')
                else:
                    self.OP = Create(tmpSrc, 'New EVENT CREATE from GMAIL')

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        event_str = "\n\n---- A SYNC EVENT ---"
        event_str += "\n    ID          OE: %s " % (self.OE.event and self.OE.event.id)
        event_str += "\n    ID          GG: %s " % (self.GG.event and self.GG.event.get('id', False))
        event_str += "\n    Name        OE: %s " % (self.OE.event and self.OE.event.name.encode('utf8'))
        event_str += "\n    Name        GG: %s " % (self.GG.event and self.GG.event.get('summary', '').encode('utf8'))
        event_str += "\n    Found       OE:%5s vs GG: %5s" % (self.OE.found, self.GG.found)
        event_str += "\n    Recurrence  OE:%5s vs GG: %5s" % (self.OE.isRecurrence, self.GG.isRecurrence)
        event_str += "\n    Instance    OE:%5s vs GG: %5s" % (self.OE.isInstance, self.GG.isInstance)
        event_str += "\n    Synchro     OE: %10s " % (self.OE.synchro)
        event_str += "\n    Update      OE: %10s " % (self.OE.update)
        event_str += "\n    Update      GG: %10s " % (self.GG.update)
        event_str += "\n    Status      OE:%5s vs GG: %5s" % (self.OE.status, self.GG.status)
        if (self.OP is None):
            event_str += "\n    Action      %s" % "---!!!---NONE---!!!---"
        else:
            event_str += "\n    Action      %s" % type(self.OP).__name__
            event_str += "\n    Source      %s" % (self.OP.src)
            event_str += "\n    comment     %s" % (self.OP.info)
        return event_str


class SyncOperation(object):
    def __init__(self, src, info, **kw):
        self.src = src
        self.info = info
        for key, val in kw.items():
            setattr(self, key, val)

    def __str__(self):
        return 'in__STR__'


class Create(SyncOperation):
    pass


class Update(SyncOperation):
    pass


class Delete(SyncOperation):
    pass


class NothingToDo(SyncOperation):
    pass


class Exclude(SyncOperation):
    pass


class GoogleCalendar(models.AbstractModel):
    STR_SERVICE = 'calendar'
    _name = 'google.%s' % STR_SERVICE

    def generate_data(self, event, isCreating=False):
        if event.allday:
            start_date = event.start_date
            final_date = (datetime.strptime(event.stop_date, tools.DEFAULT_SERVER_DATE_FORMAT) + timedelta(days=1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
            type = 'date'
            vstype = 'dateTime'
        else:
            start_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(event.start)).isoformat('T')
            final_date = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(event.stop)).isoformat('T')
            type = 'dateTime'
            vstype = 'date'
        attendee_list = []
        for attendee in event.attendee_ids:
            email = tools.email_split(attendee.email)
            email = email[0] if email else 'NoEmail@mail.com'
            attendee_list.append({
                'email': email,
                'displayName': attendee.partner_id.name,
                'responseStatus': attendee.state or 'needsAction',
            })

        reminders = []
        for alarm in event.alarm_ids:
            reminders.append({
                "method": "email" if alarm.type == "email" else "popup",
                "minutes": alarm.duration_minutes
            })
        data = {
            "summary": event.name or '',
            "description": event.description or '',
            "start": {
                type: start_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or 'UTC',
            },
            "end": {
                type: final_date,
                vstype: None,
                'timeZone': self.env.context.get('tz') or 'UTC',
            },
            "attendees": attendee_list,
            "reminders": {
                "overrides": reminders,
                "useDefault": "false"
            },
            "location": event.location or '',
            "visibility": event['privacy'] or 'public',
        }
        if event.recurrency and event.rrule:
            data["recurrence"] = ["RRULE:" + event.rrule]

        if not event.active:
            data["state"] = "cancelled"

        if not self.get_need_synchro_attendee():
            data.pop("attendees")
        if isCreating:
            other_google_ids = [other_att.google_internal_event_id for other_att in event.attendee_ids if other_att.google_internal_event_id]
            if other_google_ids:
                data["id"] = other_google_ids[0]
        return data

    def create_an_event(self, event):
        """ Create a new event in google calendar from the given event in Odoo.
            :param event : record of calendar.event to export to google calendar
        """
        data = self.generate_data(event, isCreating=True)

        url = "/calendar/v3/calendars/%s/events?fields=%s&access_token=%s" % ('primary', urllib2.quote('id,updated'), self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = json.dumps(data)
        return self.env['google.service']._do_request(url, data_json, headers, type='POST')

    def delete_an_event(self, event_id):
        """ Delete the given event in primary calendar of google cal.
            :param event_id : google cal identifier of the event to delete
        """
        params = {
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', event_id)

        return self.env['google.service']._do_request(url, params, headers, type='DELETE')

    def get_calendar_primary_id(self):
        """ In google calendar, you can have multiple calendar. But only one is
            the 'primary' one. This Calendar identifier is 'primary'.
        """
        params = {
            'fields': 'id',
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = "/calendar/v3/calendars/primary"

        try:
            status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')
        except urllib2.HTTPError, e:
            if e.code == 401:  # Token invalid / Acces unauthorized
                error_msg = _("Your token is invalid or has been revoked !")

                self.env.user.write({'google_calendar_token': False, 'google_calendar_token_validity': False})
                self.env.cr.commit()

                raise self.env['res.config.settings'].get_config_warning(error_msg)
            raise

        return (status_response(status), content['id'] or False, ask_time)

    def get_event_synchro_dict(self, lastSync=False, token=False, nextPageToken=False):
        """ Returns events on the 'primary' calendar from google cal.
            :returns dict where the key is the google_cal event id, and the value the details of the event,
                    defined at https://developers.google.com/google-apps/calendar/v3/reference/events/list
        """
        if not token:
            token = self.get_token()

        params = {
            'fields': 'items,nextPageToken',
            'access_token': token,
            'maxResults': 1000,
        }

        if lastSync:
            params['updatedMin'] = lastSync.strftime("%Y-%m-%dT%H:%M:%S.%fz")
            params['showDeleted'] = True
        else:
            params['timeMin'] = self.get_minTime().strftime("%Y-%m-%dT%H:%M:%S.%fz")

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = "/calendar/v3/calendars/%s/events" % 'primary'
        if nextPageToken:
            params['pageToken'] = nextPageToken

        status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')

        google_events_dict = {}
        for google_event in content['items']:
            google_events_dict[google_event['id']] = google_event

        if content.get('nextPageToken'):
            google_events_dict.update(
                self.get_event_synchro_dict(lastSync=lastSync, token=token, nextPageToken=content['nextPageToken'])
            )

        return google_events_dict

    def get_one_event_synchro(self, google_id):
        token = self.get_token()

        params = {
            'access_token': token,
            'maxResults': 1000,
            'showDeleted': True,
        }

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', google_id)
        try:
            status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')
        except Exception, e:
            _logger.info("Calendar Synchro - In except of get_one_event_synchro")
            _logger.info(exception_to_unicode(e))
            return False

        return status_response(status) and content or False

    def update_to_google(self, oe_event, google_event):
        url = "/calendar/v3/calendars/%s/events/%s?fields=%s&access_token=%s" % ('primary', google_event['id'], 'id,updated', self.get_token())
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data = self.generate_data(oe_event)
        data['sequence'] = google_event.get('sequence', 0)
        data_json = json.dumps(data)

        status, content, ask_time = self.env['google.service']._do_request(url, data_json, headers, type='PATCH')

        update_date = datetime.strptime(content['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
        oe_event.write({'oe_update_date': update_date})

        if self.env.context.get('curr_attendee'):
            self.env['calendar.attendee'].browse(self.env.context['curr_attendee']).write({'oe_synchro_date': update_date})

    def update_an_event(self, event):
        data = self.generate_data(event)
        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', event.google_internal_event_id)
        headers = {}
        data['access_token'] = self.get_token()

        status, response, ask_time = self.env['google.service']._do_request(url, data, headers, type='GET')
        #TO_CHECK : , if http fail, no event, do DELETE ?
        return response

    def update_recurrent_event_exclu(self, instance_id, event_ori_google_id, event_new):
        """ Update event on google calendar
            :param instance_id : new google cal identifier
            :param event_ori_google_id : origin google cal identifier
            :param event_new : record of calendar.event to modify
        """
        data = self.generate_data(event_new)
        url = "/calendar/v3/calendars/%s/events/%s?access_token=%s" % ('primary', instance_id, self.get_token())
        headers = {'Content-type': 'application/json'}

        data.update(recurringEventId=event_ori_google_id, originalStartTime=event_new.recurrent_id_date, sequence=self.get_sequence(instance_id))
        data_json = json.dumps(data)
        return self.env['google.service']._do_request(url, data_json, headers, type='PUT')

    def create_from_google(self, event, partner_id):
        context_tmp = dict(self._context, NewMeeting=True)
        res = self.with_context(context_tmp).update_from_google(False, event.GG.event, "create")
        event.OE.event_id = res
        meeting = self.env['calendar.event'].browse(res)
        attendee_record = self.env['calendar.attendee'].search([('partner_id', '=', partner_id), ('event_id', '=', res)])
        attendee_record.with_context(context_tmp).write({'oe_synchro_date': meeting.oe_update_date, 'google_internal_event_id': event.GG.event['id']})
        if meeting.recurrency:
            attendees = self.env['calendar.attendee'].sudo().search([('google_internal_event_id', '=ilike', '%s\_%%' % event.GG.event['id'])])
            excluded_recurrent_event_ids = set(attendee.event_id for attendee in attendees)
            for event in excluded_recurrent_event_ids:
                event.write({'recurrent_id': meeting.id, 'recurrent_id_date': event.start, 'user_id': meeting.user_id.id})
        return event

    def update_from_google(self, event, single_event_dict, type):
        """ Update an event in Odoo with information from google calendar
            :param event : record od calendar.event to update
            :param single_event_dict : dict of google cal event data
        """
        CalendarEvent = self.env['calendar.event'].with_context(no_mail_to_attendees=True)
        ResPartner = self.env['res.partner']
        CalendarAlarm = self.env['calendar.alarm']
        attendee_record = []
        alarm_record = set()
        partner_record = [(4, self.env.user.partner_id.id)]
        result = {}

        if self.get_need_synchro_attendee():
            for google_attendee in single_event_dict.get('attendees', []):
                partner_email = google_attendee.get('email')
                if type == "write":
                    for oe_attendee in event['attendee_ids']:
                        if oe_attendee.email == google_attendee['email']:
                            oe_attendee.write({'state': google_attendee['responseStatus'], 'google_internal_event_id': single_event_dict.get('id')})
                            google_attendee['found'] = True
                            continue

                if google_attendee.get('found'):
                    continue

                attendee = ResPartner.search([('email', '=', google_attendee['email'])], limit=1)
                if not attendee:
                    data = {
                        'email': partner_email,
                        'customer': False,
                        'name': google_attendee.get("displayName", False) or partner_email
                    }
                    attendee = ResPartner.create(data)
                attendee = attendee.read(['email'])[0]
                partner_record.append((4, attendee.get('id')))
                attendee['partner_id'] = attendee.pop('id')
                attendee['state'] = google_attendee['responseStatus']
                attendee_record.append((0, 0, attendee))
        for google_alarm in single_event_dict.get('reminders', {}).get('overrides', []):
            alarm = CalendarAlarm.search(
                [
                    ('type', '=', google_alarm['method'] if google_alarm['method'] == 'email' else 'notification'),
                    ('duration_minutes', '=', google_alarm['minutes'])
                ], limit=1
            )
            if not alarm:
                data = {
                    'type': google_alarm['method'] if google_alarm['method'] == 'email' else 'notification',
                    'duration': google_alarm['minutes'],
                    'interval': 'minutes',
                    'name': "%s minutes - %s" % (google_alarm['minutes'], google_alarm['method'])
                }
                alarm = CalendarAlarm.create(data)
            alarm_record.add(alarm.id)

        UTC = pytz.timezone('UTC')
        if single_event_dict.get('start') and single_event_dict.get('end'):  # If not cancelled

            if single_event_dict['start'].get('dateTime', False) and single_event_dict['end'].get('dateTime', False):
                date = parser.parse(single_event_dict['start']['dateTime'])
                stop = parser.parse(single_event_dict['end']['dateTime'])
                date = str(date.astimezone(UTC))[:-6]
                stop = str(stop.astimezone(UTC))[:-6]
                allday = False
            else:
                date = single_event_dict['start']['date']
                stop = single_event_dict['end']['date']
                d_end = fields.Date.from_string(stop)
                allday = True
                d_end = d_end + timedelta(days=-1)
                stop = fields.Date.to_string(d_end)

            update_date = datetime.strptime(single_event_dict['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
            result.update({
                'start': date,
                'stop': stop,
                'allday': allday
            })
        result.update({
            'attendee_ids': attendee_record,
            'partner_ids': list(set(partner_record)),
            'alarm_ids': [(6, 0, list(alarm_record))],

            'name': single_event_dict.get('summary', 'Event'),
            'description': single_event_dict.get('description', False),
            'location': single_event_dict.get('location', False),
            'privacy': single_event_dict.get('visibility', 'public'),
            'oe_update_date': update_date,
        })

        if single_event_dict.get("recurrence", False):
            rrule = [rule for rule in single_event_dict["recurrence"] if rule.startswith("RRULE:")][0][6:]
            result['rrule'] = rrule
        if type == "write":
            res = CalendarEvent.browse(event['id']).write(result)
        elif type == "copy":
            result['recurrence'] = True
            res = CalendarEvent.browse([event['id']]).write(result)
        elif type == "create":
            res = CalendarEvent.create(result).id

        if self.env.context.get('curr_attendee'):
            self.env['calendar.attendee'].with_context(no_mail_to_attendees=True).browse([self.env.context['curr_attendee']]).write({'oe_synchro_date': update_date, 'google_internal_event_id': single_event_dict.get('id', False)})
        return res

    def remove_references(self):
        current_user = self.env.user
        reset_data = {
            'google_calendar_rtoken': False,
            'google_calendar_token': False,
            'google_calendar_token_validity': False,
            'google_calendar_last_sync_date': False,
            'google_calendar_cal_id': False,
        }

        all_my_attendees = self.env['calendar.attendee'].search([('partner_id', '=', current_user.partner_id.id)])
        all_my_attendees.write({'oe_synchro_date': False, 'google_internal_event_id': False})
        return current_user.write(reset_data)

    @api.model
    def synchronize_events_cron(self):
        """ Call by the cron. """
        users = self.env['res.users'].search([('google_calendar_last_sync_date', '!=', False)])
        _logger.info("Calendar Synchro - Started by cron")

        for user_to_sync in users.ids:
            _logger.info("Calendar Synchro - Starting synchronization for a new user [%s]", user_to_sync)
            try:
                resp = self.sudo(user_to_sync).synchronize_events(lastSync=True)
                if resp.get("status") == "need_reset":
                    _logger.info("[%s] Calendar Synchro - Failed - NEED RESET  !", user_to_sync)
                else:
                    _logger.info("[%s] Calendar Synchro - Done with status : %s  !", user_to_sync, resp.get("status"))
            except Exception, e:
                _logger.info("[%s] Calendar Synchro - Exception : %s !", user_to_sync, exception_to_unicode(e))
        _logger.info("Calendar Synchro - Ended by cron")

    def synchronize_events(self, lastSync=True):
        """ This method should be called as the user to sync. """
        user_to_sync = self.ids and self.ids[0] or self.env.uid
        current_user = self.env['res.users'].sudo().browse(user_to_sync)

        recs = self.sudo(user_to_sync)
        status, current_google, ask_time = recs.get_calendar_primary_id()
        if current_user.google_calendar_cal_id:
            if current_google != current_user.google_calendar_cal_id:
                return {
                    "status": "need_reset",
                    "info": {
                        "old_name": current_user.google_calendar_cal_id,
                        "new_name": current_google
                    },
                    "url": ''
                }

            if lastSync and recs.get_last_sync_date() and not recs.get_disable_since_synchro():
                lastSync = recs.get_last_sync_date()
                _logger.info("[%s] Calendar Synchro - MODE SINCE_MODIFIED : %s !", user_to_sync, fields.Datetime.to_string(lastSync))
            else:
                lastSync = False
                _logger.info("[%s] Calendar Synchro - MODE FULL SYNCHRO FORCED", user_to_sync)
        else:
            current_user.write({'google_calendar_cal_id': current_google})
            lastSync = False
            _logger.info("[%s] Calendar Synchro - MODE FULL SYNCHRO - NEW CAL ID", user_to_sync)

        new_ids = []
        new_ids += recs.create_new_events()
        new_ids += recs.bind_recurring_events_to_google()

        res = recs.update_events(lastSync)

        current_user.write({'google_calendar_last_sync_date': ask_time})
        return {
            "status": res and "need_refresh" or "no_new_event_from_google",
            "url": ''
        }

    def create_new_events(self):
        """ Create event in google calendar for the event not already
            synchronized, for the current user.
            :returns list of new created event identifier in google calendar
        """
        new_ids = []
        my_partner_id = self.env.user.partner_id.id

        my_attendees = self.env['calendar.attendee'].with_context(virtual_id=False).search([('partner_id', '=', my_partner_id),
            ('google_internal_event_id', '=', False),
            '|',
            ('event_id.stop', '>', fields.Datetime.to_string(self.get_minTime())),
            ('event_id.final_date', '>', fields.Datetime.to_string(self.get_minTime())),
        ])
        for att in my_attendees:
            other_google_ids = [other_att.google_internal_event_id for other_att in att.event_id.attendee_ids if other_att.google_internal_event_id and other_att.id != att.id]
            for other_google_id in other_google_ids:
                if self.get_one_event_synchro(other_google_id):
                    att.write({'google_internal_event_id': other_google_id})
                    break
            else:
                if not att.event_id.recurrent_id or att.event_id.recurrent_id == 0:
                    status, response, ask_time = self.create_an_event(att.event_id)
                    if status_response(status):
                        update_date = datetime.strptime(response['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
                        att.event_id.write({'oe_update_date': update_date})
                        new_ids.append(response['id'])
                        att.write({'google_internal_event_id': response['id'], 'oe_synchro_date': update_date})
                        self.env.cr.commit()
                    else:
                        _logger.warning("Impossible to create event %s. [%s] Enable DEBUG for response detail.", att.event_id.id, status)
                        _logger.debug("Response : %s", response)
        return new_ids

    def get_context_no_virtual(self):
        """ get the current context modified to prevent virtual ids and active test. """
        return dict(self.env.context, virtual_id=False, active_test=False)

    def bind_recurring_events_to_google(self):
        new_ids = []
        CalendarAttendee = self.env['calendar.attendee']
        my_partner_id = self.env.user.partner_id.id
        context_norecurrent = self.get_context_no_virtual()
        my_attendees = CalendarAttendee.with_context(context_norecurrent).search([('partner_id', '=', my_partner_id), ('google_internal_event_id', '=', False)])
        for att in my_attendees:
            new_google_internal_event_id = False
            source_event_record = self.env['calendar.event'].browse(att.event_id.recurrent_id)
            source_attendee_record = CalendarAttendee.search([('partner_id', '=', my_partner_id), ('event_id', '=', source_event_record.id)], limit=1)
            if not source_attendee_record:
                continue

            if att.event_id.recurrent_id_date and source_event_record.allday and source_attendee_record.google_internal_event_id:
                new_google_internal_event_id = source_attendee_record.google_internal_event_id + '_' + att.event_id.recurrent_id_date.split(' ')[0].replace('-', '')
            elif att.event_id.recurrent_id_date and source_attendee_record.google_internal_event_id:
                new_google_internal_event_id = source_attendee_record.google_internal_event_id + '_' + att.event_id.recurrent_id_date.replace('-', '').replace(' ', 'T').replace(':', '') + 'Z'

            if new_google_internal_event_id:
                #TODO WARNING, NEED TO CHECK THAT EVENT and ALL instance NOT DELETE IN GMAIL BEFORE !
                try:
                    status, response, ask_time = self.update_recurrent_event_exclu(new_google_internal_event_id, source_attendee_record.google_internal_event_id, att.event_id)
                    if status_response(status):
                        att.write({'google_internal_event_id': new_google_internal_event_id})
                        new_ids.append(new_google_internal_event_id)
                        self.env.cr.commit()
                    else:
                        _logger.warning("Impossible to create event %s. [%s]", att.event_id.id, status)
                        _logger.debug("Response : %s", response)
                except:
                    pass
        return new_ids

    def update_events(self, lastSync=False):
        """ Synchronze events with google calendar : fetching, creating, updating, deleting, ... """
        CalendarEvent = self.env['calendar.event']
        CalendarAttendee = self.env['calendar.attendee']
        my_partner_id = self.env.user.partner_id.id
        context_novirtual = self.get_context_no_virtual()

        if lastSync:
            try:
                all_event_from_google = self.get_event_synchro_dict(lastSync=lastSync)
            except urllib2.HTTPError, e:
                if e.code == 410:  # GONE, Google is lost.
                    # we need to force the rollback from this cursor, because it locks my res_users but I need to write in this tuple before to raise.
                    self.env.cr.rollback()
                    self.env.user.write({'google_calendar_last_sync_date': False})
                    self.env.cr.commit()
                error_key = json.loads(str(e))
                error_key = error_key.get('error', {}).get('message', 'nc')
                error_msg = _("Google is lost... the next synchro will be a full synchro. \n\n %s") % error_key
                raise self.env['res.config.settings'].get_config_warning(error_msg)

            my_google_attendees = CalendarAttendee.with_context(context_novirtual).search([
                ('partner_id', '=', my_partner_id),
                ('google_internal_event_id', 'in', all_event_from_google.keys())
            ])
            my_google_att_ids = my_google_attendees.ids

            my_odoo_attendees = CalendarAttendee.with_context(context_novirtual).search([
                ('partner_id', '=', my_partner_id),
                ('event_id.oe_update_date', '>', lastSync and fields.Datetime.to_string(lastSync) or self.get_minTime().fields.Datetime.to_string()),
                ('google_internal_event_id', '!=', False),
            ])

            my_odoo_googleinternal_records = my_odoo_attendees.read(['google_internal_event_id', 'event_id'])

            if self.get_print_log():
                _logger.info("Calendar Synchro -  \n\nUPDATE IN GOOGLE\n%s\n\nRETRIEVE FROM OE\n%s\n\nUPDATE IN OE\n%s\n\nRETRIEVE FROM GG\n%s\n\n", all_event_from_google, my_google_att_ids, my_odoo_attendees.ids, my_odoo_googleinternal_records)

            for gi_record in my_odoo_googleinternal_records:
                active = True  # if not sure, we request google
                if gi_record.get('event_id'):
                    active = CalendarEvent.with_context(context_novirtual).browse(int(gi_record.get('event_id')[0])).active

                if gi_record.get('google_internal_event_id') and not all_event_from_google.get(gi_record.get('google_internal_event_id')) and active:
                    one_event = self.get_one_event_synchro(gi_record.get('google_internal_event_id'))
                    if one_event:
                        all_event_from_google[one_event['id']] = one_event

            my_attendees = (my_google_attendees | my_odoo_attendees)

        else:
            domain = [
                ('partner_id', '=', my_partner_id),
                ('google_internal_event_id', '!=', False),
                '|',
                ('event_id.stop', '>', fields.Datetime.to_string(self.get_minTime())),
                ('event_id.final_date', '>', fields.Datetime.to_string(self.get_minTime())),
            ]

            # Select all events from Odoo which have been already synchronized in gmail
            my_attendees = CalendarAttendee.with_context(context_novirtual).search(domain)
            all_event_from_google = self.get_event_synchro_dict(lastSync=False)

        event_to_synchronize = {}
        for att in my_attendees:
            event = att.event_id

            base_event_id = att.google_internal_event_id.rsplit('_', 1)[0]

            if base_event_id not in event_to_synchronize:
                event_to_synchronize[base_event_id] = {}

            if att.google_internal_event_id not in event_to_synchronize[base_event_id]:
                event_to_synchronize[base_event_id][att.google_internal_event_id] = SyncEvent()

            ev_to_sync = event_to_synchronize[base_event_id][att.google_internal_event_id]

            ev_to_sync.OE.attendee_id = att.id
            ev_to_sync.OE.event = event
            ev_to_sync.OE.found = True
            ev_to_sync.OE.event_id = event.id
            ev_to_sync.OE.isRecurrence = event.recurrency
            ev_to_sync.OE.isInstance = bool(event.recurrent_id and event.recurrent_id > 0)
            ev_to_sync.OE.update = event.oe_update_date
            ev_to_sync.OE.status = event.active
            ev_to_sync.OE.synchro = att.oe_synchro_date

        for event in all_event_from_google.values():
            event_id = event.get('id')
            base_event_id = event_id.rsplit('_', 1)[0]

            if base_event_id not in event_to_synchronize:
                event_to_synchronize[base_event_id] = {}

            if event_id not in event_to_synchronize[base_event_id]:
                event_to_synchronize[base_event_id][event_id] = SyncEvent()

            ev_to_sync = event_to_synchronize[base_event_id][event_id]

            ev_to_sync.GG.event = event
            ev_to_sync.GG.found = True
            ev_to_sync.GG.isRecurrence = bool(event.get('recurrence', ''))
            ev_to_sync.GG.isInstance = bool(event.get('recurringEventId', 0))
            ev_to_sync.GG.update = event.get('updated', None)  # if deleted, no date without browse event
            if ev_to_sync.GG.update:
                ev_to_sync.GG.update = ev_to_sync.GG.update.replace('T', ' ').replace('Z', '')
            ev_to_sync.GG.status = (event.get('status') != 'cancelled')

        ######################
        #   PRE-PROCESSING   #
        ######################
        for base_event in event_to_synchronize:
            for current_event in event_to_synchronize[base_event]:
                event_to_synchronize[base_event][current_event].compute_OP(modeFull=not lastSync)
            if self.get_print_log():
                if not isinstance(event_to_synchronize[base_event][current_event].OP, NothingToDo):
                    _logger.info(event_to_synchronize[base_event])

        ######################
        #      DO ACTION     #
        ######################
        for base_event in event_to_synchronize:
            event_to_synchronize[base_event] = sorted(event_to_synchronize[base_event].iteritems(), key=operator.itemgetter(0))
            for current_event in event_to_synchronize[base_event]:
                self.env.cr.commit()
                event = current_event[1]  # event is an Sync Event !
                actToDo = event.OP
                actSrc = event.OP.src

                # To avoid redefining 'self', all method below should use 'recs' instead of 'self'
                recs = self.with_context(curr_attendee=event.OE.attendee_id)

                if isinstance(actToDo, NothingToDo):
                    continue
                elif isinstance(actToDo, Create):
                    if actSrc == 'GG':
                        self.create_from_google(event, my_partner_id)
                    elif actSrc == 'OE':
                        raise "Should be never here, creation for OE is done before update !"
                    #TODO Add to batch
                elif isinstance(actToDo, Update):
                    if actSrc == 'GG':
                        recs.update_from_google(event.OE.event, event.GG.event, 'write')
                    elif actSrc == 'OE':
                        recs.update_to_google(event.OE.event, event.GG.event)
                elif isinstance(actToDo, Exclude):
                    if actSrc == 'OE':
                        recs.delete_an_event(current_event[0])
                    elif actSrc == 'GG':
                        new_google_event_id = event.GG.event['id'].rsplit('_', 1)[1]
                        if 'T' in new_google_event_id:
                            new_google_event_id = new_google_event_id.replace('T', '')[:-1]
                        else:
                            new_google_event_id = new_google_event_id + "000000"

                        if event.GG.status:
                            parent_event = {}
                            if not event_to_synchronize[base_event][0][1].OE.event_id:
                                main_ev = CalendarAttendee.with_context(context_novirtual).search([('google_internal_event_id', '=', event.GG.event['id'].rsplit('_', 1)[0])], limit=1)
                                event_to_synchronize[base_event][0][1].OE.event_id = main_ev.event_id.id

                            if event_to_synchronize[base_event][0][1].OE.event_id:
                                parent_event['id'] = "%s-%s" % (event_to_synchronize[base_event][0][1].OE.event_id, new_google_event_id)
                                res = recs.update_from_google(parent_event, event.GG.event, "copy")
                            else:
                                recs.create_from_google(event, my_partner_id)
                        else:
                            parent_oe_id = event_to_synchronize[base_event][0][1].OE.event_id
                            if parent_oe_id:
                                CalendarEvent.browse("%s-%s" % (parent_oe_id, new_google_event_id)).with_context(curr_attendee=event.OE.attendee_id).unlink(can_be_deleted=True)

                elif isinstance(actToDo, Delete):
                    if actSrc == 'GG':
                        try:
                            # if already deleted from gmail or never created
                            recs.delete_an_event(current_event[0])
                        except Exception, e:
                            if e.code in (401, 410,):
                                pass
                            else:
                                raise e
                    elif actSrc == 'OE':
                        CalendarEvent.browse(event.OE.event_id).unlink(can_be_deleted=False)
        return True

    def check_and_sync(self, oe_event, google_event):
        if datetime.strptime(oe_event.oe_update_date, "%Y-%m-%d %H:%M:%S.%f") > datetime.strptime(google_event['updated'], "%Y-%m-%dT%H:%M:%S.%fz"):
            self.update_to_google(oe_event, google_event)
        elif datetime.strptime(oe_event.oe_update_date, "%Y-%m-%d %H:%M:%S.%f") < datetime.strptime(google_event['updated'], "%Y-%m-%dT%H:%M:%S.%fz"):
            self.update_from_google(oe_event, google_event, 'write')

    def get_sequence(self, instance_id):
        params = {
            'fields': 'sequence',
            'access_token': self.get_token()
        }
        headers = {'Content-type': 'application/json'}
        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', instance_id)
        status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')
        return content.get('sequence', 0)

    #################################
    ##  MANAGE CONNEXION TO GMAIL  ##
    #################################

    def get_token(self):
        current_user = self.env.user
        if not current_user.google_calendar_token_validity or \
                fields.Datetime.from_string(current_user.google_calendar_token_validity.split('.')[0]) < (datetime.now() + timedelta(minutes=1)):
            self.do_refresh_token()
            current_user.refresh()
        return current_user.google_calendar_token

    def get_last_sync_date(self):
        current_user = self.env.user
        return current_user.google_calendar_last_sync_date and fields.Datetime.from_string(current_user.google_calendar_last_sync_date) + timedelta(minutes=0) or False

    def do_refresh_token(self):
        current_user = self.env.user
        all_token = self.env['google.service']._refresh_google_token_json(current_user.google_calendar_rtoken, self.STR_SERVICE)

        vals = {}
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')

        self.env.user.sudo().write(vals)

    def need_authorize(self):
        current_user = self.env.user
        return current_user.google_calendar_rtoken is False

    def get_calendar_scope(self, RO=False):
        readonly = '.readonly' if RO else ''
        return 'https://www.googleapis.com/auth/calendar%s' % (readonly)

    def authorize_google_uri(self, from_url='http://www.odoo.com'):
        url = self.env['google.service']._get_authorize_uri(from_url, self.STR_SERVICE, scope=self.get_calendar_scope())
        return url

    def can_authorize_google(self):
        return self.env['res.users'].has_group('base.group_erp_manager')

    @api.model
    def set_all_tokens(self, authorization_code):
        all_token = self.env['google.service']._get_google_token_json(authorization_code, self.STR_SERVICE)

        vals = {}
        vals['google_%s_rtoken' % self.STR_SERVICE] = all_token.get('refresh_token')
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')
        self.env.user.sudo().write(vals)

    def get_minTime(self):
        number_of_week = self.env['ir.config_parameter'].sudo().get_param('calendar.week_synchro', default=13)
        return datetime.now() - timedelta(weeks=number_of_week)

    def get_need_synchro_attendee(self):
        return self.env['ir.config_parameter'].sudo().get_param('calendar.block_synchro_attendee', default=True)

    def get_disable_since_synchro(self):
        return self.env['ir.config_parameter'].sudo().get_param('calendar.block_since_synchro', default=False)

    def get_print_log(self):
        return self.env['ir.config_parameter'].sudo().get_param('calendar.debug_print', default=False)
