# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import abc
from typing import Iterator, Mapping

from odoo.tools import email_normalize
from odoo.tools.misc import ReadonlyDict


class MicrosoftEvent(abc.Set):
    """
    This helper class holds the values of a Microsoft event.
    Inspired by Odoo recordset, one instance can be a single Microsoft event or a
    (immutable) set of Microsoft events.
    All usual set operations are supported (union, intersection, etc).

    :param iterable: iterable of MicrosoftCalendar instances or iterable of dictionnaries
    """

    def __init__(self, iterable=()):
        _events = {}
        for item in iterable:
            if isinstance(item, self.__class__):
                _events[item.id] = item._events[item.id]
            elif isinstance(item, Mapping):
                _events[item.get('id')] = item
            else:
                raise ValueError("Only %s or iterable of dict are supported" % self.__class__.__name__)
        self._events = ReadonlyDict(_events)

    def __iter__(self) -> Iterator['MicrosoftEvent']:
        return iter(MicrosoftEvent([vals]) for vals in self._events.values())

    def __contains__(self, microsoft_event):
        return microsoft_event.id in self._events

    def __len__(self):
        return len(self._events)

    def __bool__(self):
        return bool(self._events)

    def __getattr__(self, name):
        # ensure_one
        try:
            event, = self._events.keys()
        except ValueError:
            raise ValueError("Expected singleton: %s" % self)
        event_id = list(self._events.keys())[0]
        return self._events[event_id].get(name)

    def __repr__(self):
        return '%s%s' % (self.__class__.__name__, self.ids)

    @property
    def ids(self):
        """
        Use 'id' to return an event identifier which is specific to a calendar
        """
        return tuple(e.id for e in self)

    def microsoft_ids(self):
        return tuple(e.id for e in self)

    @property
    def uids(self):
        """
        Use 'iCalUid' to return an identifier which is unique accross all calendars
        """
        return tuple(e.iCalUId for e in self)

    def odoo_id(self, env):
        return self._odoo_id

    def _meta_odoo_id(self, microsoft_guid):
        """Returns the Odoo id stored in the Microsoft Event metadata.
        This id might not actually exists in the database.
        """
        return None

    @property
    def odoo_ids(self):
        """
        Get the list of Odoo event ids already mapped with Outlook events (self)
        """
        return tuple(e._odoo_id for e in self if e._odoo_id)

    def _load_odoo_ids_from_db(self, env, force_model=None):
        """
        Map Microsoft events to existing Odoo events:
        1) extract unmapped events only,
        2) match Odoo events and Outlook events which have both a ICalUId set,
        3) match remaining events,
        Returns the list of mapped events
        """
        mapped_events = [e.id for e in self if e._odoo_id]

        # avoid mapping events if they are already all mapped
        if len(self) == len(mapped_events):
            return self

        unmapped_events = self.filter(lambda e: e.id not in mapped_events)

        # Query events OR recurrences, get organizer_id and universal_id values by splitting microsoft_id.
        model_env = force_model if force_model is not None else self._get_model(env)
        odoo_events = model_env.with_context(active_test=False).search([
            '|',
            ('ms_universal_event_id', "in", unmapped_events.uids),
            ('microsoft_id', "in", unmapped_events.ids)
        ]).with_env(env)

        # 1. try to match unmapped events with Odoo events using their iCalUId
        unmapped_events_with_uids = unmapped_events.filter(lambda e: e.iCalUId)
        odoo_events_with_uids = odoo_events.filtered(lambda e: e.ms_universal_event_id)
        mapping = {e.ms_universal_event_id: e.id for e in odoo_events_with_uids}

        for ms_event in unmapped_events_with_uids:
            odoo_id = mapping.get(ms_event.iCalUId)
            if odoo_id:
                ms_event._events[ms_event.id]['_odoo_id'] = odoo_id
                mapped_events.append(ms_event.id)

        # 2. try to match unmapped events with Odoo events using their id
        unmapped_events = self.filter(lambda e: e.id not in mapped_events)
        mapping = {e.microsoft_id: e for e in odoo_events}

        for ms_event in unmapped_events:
            odoo_event = mapping.get(ms_event.id)
            if odoo_event:
                ms_event._events[ms_event.id]['_odoo_id'] = odoo_event.id
                mapped_events.append(ms_event.id)

                # don't forget to also set the global event ID on the Odoo event to ease
                # and improve reliability of future mappings
                odoo_event.write({
                    'microsoft_id': ms_event.id,
                    'ms_universal_event_id': ms_event.iCalUId,
                    'need_sync_m': False,
                })

        return self.filter(lambda e: e.id in mapped_events)

    def owner_id(self, env):
        """
        Indicates who is the owner of an event (i.e the organizer of the event).

        There are several possible cases:
        1) the current Odoo user is the organizer of the event according to Outlook event, so return his id.
        2) the current Odoo user is NOT the organizer and:
           2.1) we are able to find a Odoo user using the Outlook event organizer email address and we use his id,
           2.2) we are NOT able to find a Odoo user matching the organizer email address and we return False, meaning
                that no Odoo user will be able to modify this event. All modifications will be done from Outlook.
        """
        if self.isOrganizer:
            return env.user.id

        if not self.organizer:
            return False

        organizer_email = self.organizer.get('emailAddress') and email_normalize(self.organizer.get('emailAddress').get('address'))
        if organizer_email:
            # Warning: In Microsoft: 1 email = 1 user; but in Odoo several users might have the same email
            user = env['res.users'].search([('email', '=', organizer_email)], limit=1)
            return user.id if user else False
        return False

    def filter(self, func) -> 'MicrosoftEvent':
        return MicrosoftEvent(e for e in self if func(e))

    def is_recurrence(self):
        return self.type == 'seriesMaster'

    def is_recurrent(self):
        return bool(self.seriesMasterId or self.is_recurrence())

    def is_recurrent_not_master(self):
        return bool(self.seriesMasterId)

    def get_recurrence(self):
        if not self.recurrence:
            return {}
        pattern = self.recurrence['pattern']
        range = self.recurrence['range']
        end_type_dict = {
            'endDate': 'end_date',
            'noEnd': 'forever',
            'numbered': 'count',
        }
        type_dict = {
            'absoluteMonthly': 'monthly',
            'relativeMonthly': 'monthly',
            'absoluteYearly': 'yearly',
            'relativeYearly': 'yearly',
        }
        index_dict = {
            'first': '1',
            'second': '2',
            'third': '3',
            'fourth': '4',
            'last': '-1',
        }
        rrule_type = type_dict.get(pattern['type'], pattern['type'])
        interval = pattern['interval']
        result = {
            'rrule_type': rrule_type,
            'end_type': end_type_dict.get(range['type'], False),
            'interval': interval,
            'count': range['numberOfOccurrences'],
            'day': pattern['dayOfMonth'],
            'byday': index_dict.get(pattern['index'], False),
            'until': range['type'] == 'endDate' and range['endDate'],
        }

        month_by_dict = {
            'absoluteMonthly': 'date',
            'relativeMonthly': 'day',
            'absoluteYearly': 'date',
            'relativeYearly': 'day',
        }
        month_by = month_by_dict.get(pattern['type'], False)
        if month_by:
            result['month_by'] = month_by

        # daysOfWeek contains the full name of the day, the fields contain the first 3 letters (mon, tue, etc)
        week_days = [x[:3] for x in pattern.get('daysOfWeek', [])]
        for week_day in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
            result[week_day] = week_day in week_days
        if week_days:
            result['weekday'] = week_days[0].upper()
        return result

    def is_cancelled(self):
        return bool(self.isCancelled) or self.is_removed()

    def is_removed(self):
        return self.__getattr__('@removed') and self.__getattr__('@removed').get('reason') == 'deleted'

    def is_recurrence_outlier(self):
        return self.type == "exception"

    def cancelled(self):
        return self.filter(lambda e: e.is_cancelled())

    def match_with_odoo_events(self, env) -> 'MicrosoftEvent':
        """
        Match Outlook events (self) with existing Odoo events, and return the list of matched events
        """
        # first, try to match recurrences
        # Note that when a recurrence is removed, there is no field in Outlook data to identify
        # the item as a recurrence, so select all deleted items by default.
        recurrence_candidates = self.filter(lambda x: x.is_recurrence() or x.is_removed())
        mapped_recurrences = recurrence_candidates._load_odoo_ids_from_db(env, force_model=env["calendar.recurrence"])

        # then, try to match events
        events_candidates = (self - mapped_recurrences).filter(lambda x: not x.is_recurrence())
        mapped_events = events_candidates._load_odoo_ids_from_db(env)

        return mapped_recurrences | mapped_events

    def _get_model(self, env):
        if all(e.is_recurrence() for e in self):
            return env['calendar.recurrence']
        if all(not e.is_recurrence() for e in self):
            return env['calendar.event']
        raise TypeError("Mixing Microsoft events and Microsoft recurrences")
