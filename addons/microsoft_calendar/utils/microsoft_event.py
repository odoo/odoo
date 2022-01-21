# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.api import model
from typing import Iterator, Mapping
from collections import abc


class MicrosoftEvent(abc.Set):
    """This helper class holds the values of a Microsoft event.
    Inspired by Odoo recordset, one instance can be a single Microsoft event or a
    (immutable) set of Microsoft events.
    All usual set operations are supported (union, intersection, etc).

    :param iterable: iterable of MicrosoftCalendar instances or iterable of dictionnaries

    """

    def __init__(self, iterable=()):
        self._events = {}
        for item in iterable:
            if isinstance(item, self.__class__):
                self._events[item.id] = item._events[item.id]
            elif isinstance(item, Mapping):
                self._events[item.get('id')] = item
            else:
                raise ValueError("Only %s or iterable of dict are supported" % self.__class__.__name__)

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
        return tuple(e.id for e in self)

    def microsoft_ids(self):
        return tuple(e.id for e in self)

    def odoo_id(self, env):
        self.odoo_ids(env)  # load ids
        return self._odoo_id

    def _meta_odoo_id(self, microsoft_guid):
        """Returns the Odoo id stored in the Microsoft Event metadata.
        This id might not actually exists in the database.
        """
        if self.singleValueExtendedProperties:
            o_id = [prop['value'] for prop in self.singleValueExtendedProperties if prop['id'] == 'String {%s} Name odoo_id' % microsoft_guid][0]
            return int(o_id)

    def odoo_ids(self, env):
        ids = tuple(e._odoo_id for e in self if e._odoo_id)
        if len(ids) == len(self):
            return ids
        found = self._load_odoo_ids_from_db(env)
        unsure = self - found
        if unsure:
            unsure._load_odoo_ids_from_metadata(env)

        return tuple(e._odoo_id for e in self)

    def _load_odoo_ids_from_metadata(self, env):
        model_env = self._get_model(env)
        microsoft_guid = env['ir.config_parameter'].sudo().get_param('microsoft_calendar.microsoft_guid', False)
        unsure_odoo_ids = tuple(e._meta_odoo_id(microsoft_guid) for e in self)
        odoo_events = model_env.browse(_id for _id in unsure_odoo_ids if _id)

        # Extended properties are copied when splitting a recurrence Microsoft side.
        # Hence, we may have two Microsoft recurrences linked to the same Odoo id.
        # Therefore, we only consider Odoo records without microsoft id when trying
        # to match events.
        o_ids = odoo_events.exists().filtered(lambda e: not e.microsoft_id).ids
        for e in self:
            odoo_id = e._meta_odoo_id(microsoft_guid)
            if odoo_id in o_ids:
                e._events[e.id]['_odoo_id'] = odoo_id

    def _load_odoo_ids_from_db(self, env):
        model_env = self._get_model(env)
        odoo_events = model_env.with_context(active_test=False)._from_microsoft_ids(self.ids).with_env(env)
        mapping = {e.microsoft_id: e.id for e in odoo_events}
        existing_microsoft_ids = odoo_events.mapped('microsoft_id')
        for e in self:
            odoo_id = mapping.get(e.id)
            if odoo_id:
                e._events[e.id]['_odoo_id'] = odoo_id
        return self.filter(lambda e: e.id in existing_microsoft_ids)

    def owner(self, env):
        # Owner/organizer could be desynchronised between Microsoft and Odoo.
        # Let userA, userB be two new users (never synced to Microsoft before).
        # UserA creates an event in Odoo (he is the owner) but userB syncs first.
        # There is no way to insert the event into userA's calendar since we don't have
        # any authentication access. The event is therefore inserted into userB's calendar
        # (he is the orginizer in Microsoft). The "real" owner (in Odoo) is stored as an
        # extended property. There is currently no support to "transfert" ownership when
        # userA syncs his calendar the first time.
        if self.singleValueExtendedProperties:
            microsoft_guid = env['ir.config_parameter'].sudo().get_param('microsoft_calendar.microsoft_guid', False)
            real_owner_id = [prop['value'] for prop in self.singleValueExtendedProperties if prop['id'] == 'String {%s} Name owner_odoo_id' % microsoft_guid][0]
            real_owner = real_owner_id and env['res.users'].browse(int(real_owner_id))
        else:
            real_owner_id = False

        if real_owner_id and real_owner.exists():
            return real_owner
        elif self.isOrganizer:
            return env.user
        elif self.organizer and self.organizer.get('emailAddress') and self.organizer.get('emailAddress').get('address'):
            # In Microsoft: 1 email = 1 user; but in Odoo several users might have the same email
            return env['res.users'].search([('email', '=', self.organizer.get('emailAddress').get('address'))], limit=1)
        else:
            return env['res.users']

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
        if rrule_type == 'yearly':
            interval *= 12
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

        week_days = [x[:2] for x in pattern.get('daysOfWeek', [])]
        for week_day in ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']:
            result[week_day] = week_day in week_days
        if week_days:
            result['weekday'] = week_days[0].upper()
        return result

    def is_cancelled(self):
        return bool(self.isCancelled or (self.__getattr__('@removed') and self.__getattr__('@removed').get('reason') == 'deleted'))

    def is_recurrence_outlier(self):
        return bool(self.originalStartTime)

    def cancelled(self):
        return self.filter(lambda e: e.is_cancelled())

    def exists(self, env) -> 'MicrosoftEvent':
        recurrences = self.filter(MicrosoftEvent.is_recurrence)
        events = self - recurrences
        recurrences.odoo_ids(env)
        events.odoo_ids(env)

        return self.filter(lambda e: e._odoo_id)

    def _get_model(self, env):
        if all(e.is_recurrence() for e in self):
            return env['calendar.recurrence']
        if all(not e.is_recurrence() for e in self):
            return env['calendar.event']
        raise TypeError("Mixing Microsoft events and Microsoft recurrences")
