# -*- coding: utf-8 -*-

import operator
import simplejson
import urllib2

import openerp
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, exception_to_unicode

from openerp.tools.translate import _
from openerp.http import request
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from openerp.osv import fields, osv

import logging
_logger = logging.getLogger(__name__)


def status_response(status, substr=False):
    if substr:
        return int(str(status)[0])
    else:
        return status_response(status, substr=True) == 2


class Meta(type):
    """ This Meta class allow to define class as a structure, and so instancied variable
        in __init__ to avoid to have side effect alike 'static' variable """
    def __new__(typ, name, parents, attrs):
        methods = dict((k, v) for k, v in attrs.iteritems()
                       if callable(v))
        attrs = dict((k, v) for k, v in attrs.iteritems()
                     if not callable(v))

        def init(self, **kw):
            for k, v in attrs.iteritems():
                setattr(self, k, v)
            for k, v in kw.iteritems():
                assert k in attrs
                setattr(self, k, v)

        methods['__init__'] = init
        methods['__getitem__'] = getattr
        return type.__new__(typ, name, parents, methods)


class Struct(object):
    __metaclass__ = Meta


class OpenerpEvent(Struct):
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
        self.OE = OpenerpEvent()
        self.GG = GmailEvent()
        self.OP = None

    def __getitem__(self, key):
        return getattr(self, key)

    def compute_OP(self, modeFull=True):
        #If event are already in Gmail and in OpenERP
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

                    #if self.OP.action == None:
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

        # New in openERP...  Create on create_events of synchronize function
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
        myPrint = "\n\n---- A SYNC EVENT ---"
        myPrint += "\n    ID          OE: %s " % (self.OE.event and self.OE.event.id)
        myPrint += "\n    ID          GG: %s " % (self.GG.event and self.GG.event.get('id', False))
        myPrint += "\n    Name        OE: %s " % (self.OE.event and self.OE.event.name.encode('utf8'))
        myPrint += "\n    Name        GG: %s " % (self.GG.event and self.GG.event.get('summary', '').encode('utf8'))
        myPrint += "\n    Found       OE:%5s vs GG: %5s" % (self.OE.found, self.GG.found)
        myPrint += "\n    Recurrence  OE:%5s vs GG: %5s" % (self.OE.isRecurrence, self.GG.isRecurrence)
        myPrint += "\n    Instance    OE:%5s vs GG: %5s" % (self.OE.isInstance, self.GG.isInstance)
        myPrint += "\n    Synchro     OE: %10s " % (self.OE.synchro)
        myPrint += "\n    Update      OE: %10s " % (self.OE.update)
        myPrint += "\n    Update      GG: %10s " % (self.GG.update)
        myPrint += "\n    Status      OE:%5s vs GG: %5s" % (self.OE.status, self.GG.status)
        if (self.OP is None):
            myPrint += "\n    Action      %s" % "---!!!---NONE---!!!---"
        else:
            myPrint += "\n    Action      %s" % type(self.OP).__name__
            myPrint += "\n    Source      %s" % (self.OP.src)
            myPrint += "\n    comment     %s" % (self.OP.info)
        return myPrint


class SyncOperation(object):
    def __init__(self, src, info, **kw):
        self.src = src
        self.info = info
        for k, v in kw.items():
            setattr(self, k, v)

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


class google_calendar(osv.AbstractModel):
    STR_SERVICE = 'calendar'
    _name = 'google.%s' % STR_SERVICE

    def generate_data(self, cr, uid, event, isCreating=False, context=None):
        if not context:
            context = {}
        if event.allday:
            start_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.start, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T').split('T')[0]
            final_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.start, tools.DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=event.duration) + timedelta(days=isCreating and 1 or 0), context=context).isoformat('T').split('T')[0]
            type = 'date'
            vstype = 'dateTime'
        else:
            start_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.start, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T')
            final_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(event.stop, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context).isoformat('T')
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
                'timeZone': context.get('tz', 'UTC'),
            },
            "end": {
                type: final_date,
                vstype: None,
                'timeZone': context.get('tz', 'UTC'),
            },
            "attendees": attendee_list,
            "reminders": {
                "overrides": reminders,
                "useDefault": "false"
            },
            "location": event.location or '',
            "visibility": event['class'] or 'public',
        }
        if event.recurrency and event.rrule:
            data["recurrence"] = ["RRULE:" + event.rrule]

        if not event.active:
            data["state"] = "cancelled"

        if not self.get_need_synchro_attendee(cr, uid, context=context):
            data.pop("attendees")
        return data

    def create_an_event(self, cr, uid, event, context=None):
        gs_pool = self.pool['google.service']
        data = self.generate_data(cr, uid, event, isCreating=True, context=context)

        url = "/calendar/v3/calendars/%s/events?fields=%s&access_token=%s" % ('primary', urllib2.quote('id,updated'), self.get_token(cr, uid, context))
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data_json = simplejson.dumps(data)

        return gs_pool._do_request(cr, uid, url, data_json, headers, type='POST', context=context)

    def delete_an_event(self, cr, uid, event_id, context=None):
        gs_pool = self.pool['google.service']

        params = {
            'access_token': self.get_token(cr, uid, context)
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', event_id)

        return gs_pool._do_request(cr, uid, url, params, headers, type='DELETE', context=context)

    def get_calendar_primary_id(self, cr, uid, context=None):
        params = {
            'fields': 'id',
            'access_token': self.get_token(cr, uid, context)
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = "/calendar/v3/calendars/primary"

        try:
            st, content, ask_time = self.pool['google.service']._do_request(cr, uid, url, params, headers, type='GET', context=context)
        except Exception, e:

            if (e.code == 401):  # Token invalid / Acces unauthorized
                error_msg = "Your token is invalid or has been revoked !"

                registry = openerp.modules.registry.RegistryManager.get(request.session.db)
                with registry.cursor() as cur:
                    self.pool['res.users'].write(cur, SUPERUSER_ID, [uid], {'google_calendar_token': False, 'google_calendar_token_validity': False}, context=context)

                raise self.pool.get('res.config.settings').get_config_warning(cr, _(error_msg), context=context)
            raise

        return (status_response(st), content['id'] or False, ask_time)

    def get_event_synchro_dict(self, cr, uid, lastSync=False, token=False, nextPageToken=False, context=None):
        if not token:
            token = self.get_token(cr, uid, context)

        params = {
            'fields': 'items,nextPageToken',
            'access_token': token,
            'maxResults': 1000,
            #'timeMin': self.get_minTime(cr, uid, context=context).strftime("%Y-%m-%dT%H:%M:%S.%fz"),
        }

        if lastSync:
            params['updatedMin'] = lastSync.strftime("%Y-%m-%dT%H:%M:%S.%fz")
            params['showDeleted'] = True
        else:
            params['timeMin'] = self.get_minTime(cr, uid, context=context).strftime("%Y-%m-%dT%H:%M:%S.%fz")

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = "/calendar/v3/calendars/%s/events" % 'primary'
        if nextPageToken:
            params['pageToken'] = nextPageToken

        status, content, ask_time = self.pool['google.service']._do_request(cr, uid, url, params, headers, type='GET', context=context)

        google_events_dict = {}
        for google_event in content['items']:
            google_events_dict[google_event['id']] = google_event

        if content.get('nextPageToken'):
            google_events_dict.update(
                self.get_event_synchro_dict(cr, uid, lastSync=lastSync, token=token, nextPageToken=content['nextPageToken'], context=context)
            )

        return google_events_dict

    def get_one_event_synchro(self, cr, uid, google_id, context=None):
        token = self.get_token(cr, uid, context)

        params = {
            'access_token': token,
            'maxResults': 1000,
            'showDeleted': True,
        }

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', google_id)
        try:
            status, content, ask_time = self.pool['google.service']._do_request(cr, uid, url, params, headers, type='GET', context=context)
        except:
            _logger.info("Calendar Synchro - In except of get_one_event_synchro")
            pass

        return status_response(status) and content or False

    def update_to_google(self, cr, uid, oe_event, google_event, context):
        calendar_event = self.pool['calendar.event']

        url = "/calendar/v3/calendars/%s/events/%s?fields=%s&access_token=%s" % ('primary', google_event['id'], 'id,updated', self.get_token(cr, uid, context))
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data = self.generate_data(cr, uid, oe_event, context=context)
        data['sequence'] = google_event.get('sequence', 0)
        data_json = simplejson.dumps(data)

        status, content, ask_time = self.pool['google.service']._do_request(cr, uid, url, data_json, headers, type='PATCH', context=context)

        update_date = datetime.strptime(content['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
        calendar_event.write(cr, uid, [oe_event.id], {'oe_update_date': update_date})

        if context['curr_attendee']:
            self.pool['calendar.attendee'].write(cr, uid, [context['curr_attendee']], {'oe_synchro_date': update_date}, context)

    def update_an_event(self, cr, uid, event, context=None):
        data = self.generate_data(cr, uid, event, context=context)

        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', event.google_internal_event_id)
        headers = {}
        data['access_token'] = self.get_token(cr, uid, context)

        status, response, ask_time = self.pool['google.service']._do_request(cr, uid, url, data, headers, type='GET', context=context)
        #TO_CHECK : , if http fail, no event, do DELETE ?
        return response

    def update_recurrent_event_exclu(self, cr, uid, instance_id, event_ori_google_id, event_new, context=None):
        gs_pool = self.pool['google.service']

        data = self.generate_data(cr, uid, event_new, context=context)

        data['recurringEventId'] = event_ori_google_id
        data['originalStartTime'] = event_new.recurrent_id_date

        url = "/calendar/v3/calendars/%s/events/%s?access_token=%s" % ('primary', instance_id, self.get_token(cr, uid, context))
        headers = {'Content-type': 'application/json'}

        data['sequence'] = self.get_sequence(cr, uid, instance_id, context)

        data_json = simplejson.dumps(data)
        return gs_pool._do_request(cr, uid, url, data_json, headers, type='PUT', context=context)

    def update_from_google(self, cr, uid, event, single_event_dict, type, context):
        if context is None:
            context = []

        calendar_event = self.pool['calendar.event']
        res_partner_obj = self.pool['res.partner']
        calendar_attendee_obj = self.pool['calendar.attendee']
        calendar_alarm_obj = self.pool['calendar.alarm']
        user_obj = self.pool['res.users']
        myPartnerID = user_obj.browse(cr, uid, uid, context).partner_id.id
        attendee_record = []
        alarm_record = set()
        partner_record = [(4, myPartnerID)]
        result = {}

        if self.get_need_synchro_attendee(cr, uid, context=context):
            for google_attendee in single_event_dict.get('attendees', []):
                partner_email = google_attendee.get('email', False)
                if type == "write":
                    for oe_attendee in event['attendee_ids']:
                        if oe_attendee.email == partner_email:
                            calendar_attendee_obj.write(cr, uid, [oe_attendee.id], {'state': google_attendee['responseStatus'], 'google_internal_event_id': single_event_dict.get('id')}, context=context)
                            google_attendee['found'] = True
                            continue

                if google_attendee.get('found'):
                    continue

                attendee_id = res_partner_obj.search(cr, uid, [('email', '=', partner_email)], context=context)
                if not attendee_id:
                    data = {
                        'email': partner_email,
                        'customer': False,
                        'name': google_attendee.get("displayName", False) or partner_email
                    }
                    attendee_id = [res_partner_obj.create(cr, uid, data, context=context)]
                attendee = res_partner_obj.read(cr, uid, attendee_id[0], ['email'], context=context)
                partner_record.append((4, attendee.get('id')))
                attendee['partner_id'] = attendee.pop('id')
                attendee['state'] = google_attendee['responseStatus']
                attendee['google_internal_event_id'] = single_event_dict.get('id')
                attendee_record.append((0, 0, attendee))
        for google_alarm in single_event_dict.get('reminders', {}).get('overrides', []):
            alarm_id = calendar_alarm_obj.search(
                cr,
                uid,
                [
                    ('type', '=', google_alarm['method'] if google_alarm['method'] == 'email' else 'notification'),
                    ('duration_minutes', '=', google_alarm['minutes'])
                ],
                context=context
            )
            if not alarm_id:
                data = {
                    'type': google_alarm['method'] if google_alarm['method'] == 'email' else 'notification',
                    'duration': google_alarm['minutes'],
                    'interval': 'minutes',
                    'name': "%s minutes - %s" % (google_alarm['minutes'], google_alarm['method'])
                }
                alarm_id = [calendar_alarm_obj.create(cr, uid, data, context=context)]
            alarm_record.add(alarm_id[0])

        UTC = pytz.timezone('UTC')
        if single_event_dict.get('start') and single_event_dict.get('end'):  # If not cancelled

            if single_event_dict['start'].get('dateTime', False) and single_event_dict['end'].get('dateTime', False):
                date = parser.parse(single_event_dict['start']['dateTime'])
                stop = parser.parse(single_event_dict['end']['dateTime'])
                date = str(date.astimezone(UTC))[:-6]
                stop = str(stop.astimezone(UTC))[:-6]
                allday = False
            else:
                date = (single_event_dict['start']['date'])
                stop = (single_event_dict['end']['date'])
                d_end = datetime.strptime(stop, DEFAULT_SERVER_DATE_FORMAT)
                allday = True
                d_end = d_end + timedelta(days=-1)
                stop = d_end.strftime(DEFAULT_SERVER_DATE_FORMAT)

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
            'class': single_event_dict.get('visibility', 'public'),
            'oe_update_date': update_date,
        })

        if single_event_dict.get("recurrence", False):
            rrule = [rule for rule in single_event_dict["recurrence"] if rule.startswith("RRULE:")][0][6:]
            result['rrule'] = rrule

        context = dict(context or {}, no_mail_to_attendees=True)
        if type == "write":
            res = calendar_event.write(cr, uid, event['id'], result, context=context)
        elif type == "copy":
            result['recurrence'] = True
            res = calendar_event.write(cr, uid, [event['id']], result, context=context)
        elif type == "create":
            res = calendar_event.create(cr, uid, result, context=context)

        if context['curr_attendee']:
            self.pool['calendar.attendee'].write(cr, uid, [context['curr_attendee']], {'oe_synchro_date': update_date, 'google_internal_event_id': single_event_dict.get('id', False)}, context)
        return res

    def remove_references(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        reset_data = {
            'google_calendar_rtoken': False,
            'google_calendar_token': False,
            'google_calendar_token_validity': False,
            'google_calendar_last_sync_date': False,
            'google_calendar_cal_id': False,
        }

        all_my_attendees = self.pool['calendar.attendee'].search(cr, uid, [('partner_id', '=', current_user.partner_id.id)], context=context)
        self.pool['calendar.attendee'].write(cr, uid, all_my_attendees, {'oe_synchro_date': False, 'google_internal_event_id': False}, context=context)
        current_user.write(reset_data)
        return True

    def synchronize_events_cron(self, cr, uid, context=None):
        ids = self.pool['res.users'].search(cr, uid, [('google_calendar_last_sync_date', '!=', False)], context=context)
        _logger.info("Calendar Synchro - Started by cron")

        for user_to_sync in ids:
            _logger.info("Calendar Synchro - Starting synchronization for a new user [%s] " % user_to_sync)
            try:
                resp = self.synchronize_events(cr, user_to_sync, False, lastSync=True, context=None)
                if resp.get("status") == "need_reset":
                    _logger.info("[%s] Calendar Synchro - Failed - NEED RESET  !" % user_to_sync)
                else:
                    _logger.info("[%s] Calendar Synchro - Done with status : %s  !" % (user_to_sync, resp.get("status")))
            except Exception, e:
                _logger.info("[%s] Calendar Synchro - Exception : %s !" % (user_to_sync, exception_to_unicode(e)))
        _logger.info("Calendar Synchro - Ended by cron")

    def synchronize_events(self, cr, uid, ids, lastSync=True, context=None):
        if context is None:
            context = {}

        # def isValidSync(syncToken):
        #     gs_pool = self.pool['google.service']
        #     params = {
        #         'maxResults': 1,
        #         'fields': 'id',
        #         'access_token': self.get_token(cr, uid, context),
        #         'syncToken': syncToken,
        #     }
        #     url = "/calendar/v3/calendars/primary/events"
        #     status, response = gs_pool._do_request(cr, uid, url, params, type='GET', context=context)
        #     return int(status) != 410

        user_to_sync = ids and ids[0] or uid
        current_user = self.pool['res.users'].browse(cr, SUPERUSER_ID, user_to_sync, context=context)

        st, current_google, ask_time = self.get_calendar_primary_id(cr, user_to_sync, context=context)

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

            if lastSync and self.get_last_sync_date(cr, user_to_sync, context=context) and not self.get_disable_since_synchro(cr, user_to_sync, context=context):
                lastSync = self.get_last_sync_date(cr, user_to_sync, context)
                _logger.info("[%s] Calendar Synchro - MODE SINCE_MODIFIED : %s !" % (user_to_sync, lastSync.strftime(DEFAULT_SERVER_DATETIME_FORMAT)))
            else:
                lastSync = False
                _logger.info("[%s] Calendar Synchro - MODE FULL SYNCHRO FORCED" % user_to_sync)
        else:
            current_user.write({'google_calendar_cal_id': current_google})
            lastSync = False
            _logger.info("[%s] Calendar Synchro - MODE FULL SYNCHRO - NEW CAL ID" % user_to_sync)

        new_ids = []
        new_ids += self.create_new_events(cr, user_to_sync, context=context)
        new_ids += self.bind_recurring_events_to_google(cr, user_to_sync, context)

        res = self.update_events(cr, user_to_sync, lastSync, context)

        current_user.write({'google_calendar_last_sync_date': ask_time})
        return {
            "status": res and "need_refresh" or "no_new_event_from_google",
            "url": ''
        }

    def create_new_events(self, cr, uid, context=None):
        if context is None:
            context = {}

        new_ids = []
        ev_obj = self.pool['calendar.event']
        att_obj = self.pool['calendar.attendee']
        user_obj = self.pool['res.users']
        myPartnerID = user_obj.browse(cr, uid, uid, context=context).partner_id.id

        context_norecurrent = context.copy()
        context_norecurrent['virtual_id'] = False
        my_att_ids = att_obj.search(cr, uid, [('partner_id', '=', myPartnerID),
                                    ('google_internal_event_id', '=', False),
                                    '|',
                                    ('event_id.stop', '>', self.get_minTime(cr, uid, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                    ('event_id.final_date', '>', self.get_minTime(cr, uid, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                    ], context=context_norecurrent)
        for att in att_obj.browse(cr, uid, my_att_ids, context=context):
            if not att.event_id.recurrent_id or att.event_id.recurrent_id == 0:
                st, response, ask_time = self.create_an_event(cr, uid, att.event_id, context=context)
                if status_response(st):
                    update_date = datetime.strptime(response['updated'], "%Y-%m-%dT%H:%M:%S.%fz")
                    ev_obj.write(cr, uid, att.event_id.id, {'oe_update_date': update_date})
                    new_ids.append(response['id'])
                    att_obj.write(cr, uid, [att.id for att in att.event_id.attendee_ids], {'google_internal_event_id': response['id'], 'oe_synchro_date': update_date})
                    cr.commit()
                else:
                    _logger.warning("Impossible to create event %s. [%s]" % (att.event_id.id, st))
                    _logger.warning("Response : %s" % response)
        return new_ids

    def get_context_no_virtual(self, context):
        context_norecurrent = context.copy()
        context_norecurrent['virtual_id'] = False
        context_norecurrent['active_test'] = False
        return context_norecurrent

    def bind_recurring_events_to_google(self, cr, uid, context=None):
        if context is None:
            context = {}

        new_ids = []
        ev_obj = self.pool['calendar.event']
        att_obj = self.pool['calendar.attendee']
        user_obj = self.pool['res.users']
        myPartnerID = user_obj.browse(cr, uid, uid, context=context).partner_id.id

        context_norecurrent = self.get_context_no_virtual(context)
        my_att_ids = att_obj.search(cr, uid, [('partner_id', '=', myPartnerID), ('google_internal_event_id', '=', False)], context=context_norecurrent)

        for att in att_obj.browse(cr, uid, my_att_ids, context=context):
            if att.event_id.recurrent_id and att.event_id.recurrent_id > 0:
                new_google_internal_event_id = False
                source_event_record = ev_obj.browse(cr, uid, att.event_id.recurrent_id, context)
                source_attendee_record_id = att_obj.search(cr, uid, [('partner_id', '=', myPartnerID), ('event_id', '=', source_event_record.id)], context=context)
                if not source_attendee_record_id:
                    continue
                source_attendee_record = att_obj.browse(cr, uid, source_attendee_record_id, context)[0]

                if att.event_id.recurrent_id_date and source_event_record.allday and source_attendee_record.google_internal_event_id:
                    new_google_internal_event_id = source_attendee_record.google_internal_event_id + '_' + att.event_id.recurrent_id_date.split(' ')[0].replace('-', '')
                elif att.event_id.recurrent_id_date and source_attendee_record.google_internal_event_id:
                    new_google_internal_event_id = source_attendee_record.google_internal_event_id + '_' + att.event_id.recurrent_id_date.replace('-', '').replace(' ', 'T').replace(':', '') + 'Z'

                if new_google_internal_event_id:
                    #TODO WARNING, NEED TO CHECK THAT EVENT and ALL instance NOT DELETE IN GMAIL BEFORE !
                    try:
                        st, response, ask_time = self.update_recurrent_event_exclu(cr, uid, new_google_internal_event_id, source_attendee_record.google_internal_event_id, att.event_id, context=context)
                        if status_response(st):
                            att_obj.write(cr, uid, [att.id], {'google_internal_event_id': new_google_internal_event_id}, context=context)
                            new_ids.append(new_google_internal_event_id)
                            cr.commit()
                        else:
                            _logger.warning("Impossible to create event %s. [%s]" % (att.event_id.id, st))
                            _logger.warning("Response : %s" % response)
                    except:
                        pass
        return new_ids

    def update_events(self, cr, uid, lastSync=False, context=None):
        context = dict(context or {})

        calendar_event = self.pool['calendar.event']
        user_obj = self.pool['res.users']
        att_obj = self.pool['calendar.attendee']
        myPartnerID = user_obj.browse(cr, uid, uid, context=context).partner_id.id
        context_novirtual = self.get_context_no_virtual(context)

        if lastSync:
            try:
                all_event_from_google = self.get_event_synchro_dict(cr, uid, lastSync=lastSync, context=context)
            except urllib2.HTTPError, e:
                if e.code == 410:  # GONE, Google is lost.
                    # we need to force the rollback from this cursor, because it locks my res_users but I need to write in this tuple before to raise.
                    cr.rollback()
                    registry = openerp.modules.registry.RegistryManager.get(request.session.db)
                    with registry.cursor() as cur:
                        self.pool['res.users'].write(cur, SUPERUSER_ID, [uid], {'google_calendar_last_sync_date': False}, context=context)
                error_key = simplejson.loads(str(e))
                error_key = error_key.get('error', {}).get('message', 'nc')
                error_msg = "Google is lost... the next synchro will be a full synchro. \n\n %s" % error_key
                raise self.pool.get('res.config.settings').get_config_warning(cr, _(error_msg), context=context)

            my_google_att_ids = att_obj.search(cr, uid, [
                ('partner_id', '=', myPartnerID),
                ('google_internal_event_id', 'in', all_event_from_google.keys())
            ], context=context_novirtual)

            my_openerp_att_ids = att_obj.search(cr, uid, [
                ('partner_id', '=', myPartnerID),
                ('event_id.oe_update_date', '>', lastSync and lastSync.strftime(DEFAULT_SERVER_DATETIME_FORMAT) or self.get_minTime(cr, uid, context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                ('google_internal_event_id', '!=', False),
            ], context=context_novirtual)

            my_openerp_googleinternal_ids = att_obj.read(cr, uid, my_openerp_att_ids, ['google_internal_event_id', 'event_id'], context=context_novirtual)

            if self.get_print_log(cr, uid, context=context):
                _logger.info("Calendar Synchro -  \n\nUPDATE IN GOOGLE\n%s\n\nRETRIEVE FROM OE\n%s\n\nUPDATE IN OE\n%s\n\nRETRIEVE FROM GG\n%s\n\n" % (all_event_from_google, my_google_att_ids, my_openerp_att_ids, my_openerp_googleinternal_ids))

            for giid in my_openerp_googleinternal_ids:
                active = True  # if not sure, we request google
                if giid.get('event_id'):
                    active = calendar_event.browse(cr, uid, int(giid.get('event_id')[0]), context=context_novirtual).active

                if giid.get('google_internal_event_id') and not all_event_from_google.get(giid.get('google_internal_event_id')) and active:
                    one_event = self.get_one_event_synchro(cr, uid, giid.get('google_internal_event_id'), context=context)
                    if one_event:
                        all_event_from_google[one_event['id']] = one_event

            my_att_ids = list(set(my_google_att_ids + my_openerp_att_ids))

        else:
            domain = [
                ('partner_id', '=', myPartnerID),
                ('google_internal_event_id', '!=', False),
                '|',
                ('event_id.stop', '>', self.get_minTime(cr, uid, context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                ('event_id.final_date', '>', self.get_minTime(cr, uid, context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
            ]

            # Select all events from OpenERP which have been already synchronized in gmail
            my_att_ids = att_obj.search(cr, uid, domain, context=context_novirtual)
            all_event_from_google = self.get_event_synchro_dict(cr, uid, lastSync=False, context=context)

        event_to_synchronize = {}
        for att in att_obj.browse(cr, uid, my_att_ids, context=context):
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
            if self.get_print_log(cr, uid, context=context):
                if not isinstance(event_to_synchronize[base_event][current_event].OP, NothingToDo):
                    _logger.info(event_to_synchronize[base_event])

        ######################
        #      DO ACTION     #
        ######################
        for base_event in event_to_synchronize:
            event_to_synchronize[base_event] = sorted(event_to_synchronize[base_event].iteritems(), key=operator.itemgetter(0))
            for current_event in event_to_synchronize[base_event]:
                cr.commit()
                event = current_event[1]  # event is an Sync Event !
                actToDo = event.OP
                actSrc = event.OP.src

                context['curr_attendee'] = event.OE.attendee_id

                if isinstance(actToDo, NothingToDo):
                    continue
                elif isinstance(actToDo, Create):
                    context_tmp = context.copy()
                    context_tmp['NewMeeting'] = True
                    if actSrc == 'GG':
                        res = self.update_from_google(cr, uid, False, event.GG.event, "create", context=context_tmp)
                        event.OE.event_id = res
                        meeting = calendar_event.browse(cr, uid, res, context=context)
                        attendee_record_id = att_obj.search(cr, uid, [('partner_id', '=', myPartnerID), ('event_id', '=', res)], context=context)
                        self.pool['calendar.attendee'].write(cr, uid, attendee_record_id, {'oe_synchro_date': meeting.oe_update_date, 'google_internal_event_id': event.GG.event['id']}, context=context_tmp)
                    elif actSrc == 'OE':
                        raise "Should be never here, creation for OE is done before update !"
                    #TODO Add to batch
                elif isinstance(actToDo, Update):
                    if actSrc == 'GG':
                        self.update_from_google(cr, uid, event.OE.event, event.GG.event, 'write', context)
                    elif actSrc == 'OE':
                        self.update_to_google(cr, uid, event.OE.event, event.GG.event, context)
                elif isinstance(actToDo, Exclude):
                    if actSrc == 'OE':
                        self.delete_an_event(cr, uid, current_event[0], context=context)
                    elif actSrc == 'GG':
                        new_google_event_id = event.GG.event['id'].rsplit('_', 1)[1]
                        if 'T' in new_google_event_id:
                            new_google_event_id = new_google_event_id.replace('T', '')[:-1]
                        else:
                            new_google_event_id = new_google_event_id + "000000"

                        if event.GG.status:
                            parent_event = {}
                            if not event_to_synchronize[base_event][0][1].OE.event_id:
                                main_ev = att_obj.search_read(cr, uid, [('google_internal_event_id', '=', event.GG.event['id'].rsplit('_', 1)[0])], fields=['event_id'], context=context_novirtual)
                                event_to_synchronize[base_event][0][1].OE.event_id = main_ev[0].get('event_id')[0]

                            parent_event['id'] = "%s-%s" % (event_to_synchronize[base_event][0][1].OE.event_id, new_google_event_id)
                            res = self.update_from_google(cr, uid, parent_event, event.GG.event, "copy", context)
                        else:
                            parent_oe_id = event_to_synchronize[base_event][0][1].OE.event_id
                            if parent_oe_id:
                                calendar_event.unlink(cr, uid, "%s-%s" % (parent_oe_id, new_google_event_id), can_be_deleted=True, context=context)

                elif isinstance(actToDo, Delete):
                    if actSrc == 'GG':
                        try:
                            self.delete_an_event(cr, uid, current_event[0], context=context)
                        except Exception, e:
                            error = simplejson.loads(e.read())
                            error_nr = error.get('error', {}).get('code')
                            # if already deleted from gmail or never created
                            if error_nr in (404, 410,):
                                pass
                            else:
                                raise e
                    elif actSrc == 'OE':
                        calendar_event.unlink(cr, uid, event.OE.event_id, can_be_deleted=False, context=context)
        return True

    def check_and_sync(self, cr, uid, oe_event, google_event, context):
        if datetime.strptime(oe_event.oe_update_date, "%Y-%m-%d %H:%M:%S.%f") > datetime.strptime(google_event['updated'], "%Y-%m-%dT%H:%M:%S.%fz"):
            self.update_to_google(cr, uid, oe_event, google_event, context)
        elif datetime.strptime(oe_event.oe_update_date, "%Y-%m-%d %H:%M:%S.%f") < datetime.strptime(google_event['updated'], "%Y-%m-%dT%H:%M:%S.%fz"):
            self.update_from_google(cr, uid, oe_event, google_event, 'write', context)

    def get_sequence(self, cr, uid, instance_id, context=None):
        gs_pool = self.pool['google.service']

        params = {
            'fields': 'sequence',
            'access_token': self.get_token(cr, uid, context)
        }

        headers = {'Content-type': 'application/json'}

        url = "/calendar/v3/calendars/%s/events/%s" % ('primary', instance_id)

        st, content, ask_time = gs_pool._do_request(cr, uid, url, params, headers, type='GET', context=context)
        return content.get('sequence', 0)
#################################
##  MANAGE CONNEXION TO GMAIL  ##
#################################

    def get_token(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        if not current_user.google_calendar_token_validity or \
                datetime.strptime(current_user.google_calendar_token_validity.split('.')[0], DEFAULT_SERVER_DATETIME_FORMAT) < (datetime.now() + timedelta(minutes=1)):
            self.do_refresh_token(cr, uid, context=context)
            current_user.refresh()
        return current_user.google_calendar_token

    def get_last_sync_date(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        return current_user.google_calendar_last_sync_date and datetime.strptime(current_user.google_calendar_last_sync_date, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(minutes=0) or False

    def do_refresh_token(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        gs_pool = self.pool['google.service']

        all_token = gs_pool._refresh_google_token_json(cr, uid, current_user.google_calendar_rtoken, self.STR_SERVICE, context=context)

        vals = {}
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')

        self.pool['res.users'].write(cr, SUPERUSER_ID, uid, vals, context=context)

    def need_authorize(self, cr, uid, context=None):
        current_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        return current_user.google_calendar_rtoken is False

    def get_calendar_scope(self, RO=False):
        readonly = RO and '.readonly' or ''
        return 'https://www.googleapis.com/auth/calendar%s' % (readonly)

    def authorize_google_uri(self, cr, uid, from_url='http://www.openerp.com', context=None):
        url = self.pool['google.service']._get_authorize_uri(cr, uid, from_url, self.STR_SERVICE, scope=self.get_calendar_scope(), context=context)
        return url

    def can_authorize_google(self, cr, uid, context=None):
        return self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager')

    def set_all_tokens(self, cr, uid, authorization_code, context=None):
        gs_pool = self.pool['google.service']
        all_token = gs_pool._get_google_token_json(cr, uid, authorization_code, self.STR_SERVICE, context=context)

        vals = {}
        vals['google_%s_rtoken' % self.STR_SERVICE] = all_token.get('refresh_token')
        vals['google_%s_token_validity' % self.STR_SERVICE] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_%s_token' % self.STR_SERVICE] = all_token.get('access_token')
        self.pool['res.users'].write(cr, SUPERUSER_ID, uid, vals, context=context)

    def get_minTime(self, cr, uid, context=None):
        number_of_week = int(self.pool['ir.config_parameter'].get_param(cr, uid, 'calendar.week_synchro', default=13))
        return datetime.now() - timedelta(weeks=number_of_week)

    def get_need_synchro_attendee(self, cr, uid, context=None):
        return self.pool['ir.config_parameter'].get_param(cr, uid, 'calendar.block_synchro_attendee', default=True)

    def get_disable_since_synchro(self, cr, uid, context=None):
        return self.pool['ir.config_parameter'].get_param(cr, uid, 'calendar.block_since_synchro', default=False)

    def get_print_log(self, cr, uid, context=None):
        return self.pool['ir.config_parameter'].get_param(cr, uid, 'calendar.debug_print', default=False)


class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'google_calendar_rtoken': fields.char('Refresh Token'),
        'google_calendar_token': fields.char('User token'),
        'google_calendar_token_validity': fields.datetime('Token Validity'),
        'google_calendar_last_sync_date': fields.datetime('Last synchro date'),
        'google_calendar_cal_id': fields.char('Calendar ID', help='Last Calendar ID who has been synchronized. If it is changed, we remove \
all links between GoogleID and Odoo Google Internal ID')
    }


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
