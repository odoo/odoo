# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from functools import lru_cache
import logging
import random

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"
    _populate_sizes = {
        'small': 10,
        'medium': 1000,
        'large': 10000,
    }
    _populate_dependencies = ["res.partner", "res.users"]

    def _update_attendees(self, records):
        for r in records:
            # add the organizer in the partners list
            if r.user_id:
                r.partner_ids += r.user_id.partner_id

            # generate a random attendee state
            if r.attendee_ids:
                for a in r.attendee_ids:
                    a.state = random.choices(
                        ['needsAction', 'tentative', 'declined', 'accepted'],
                        weights=[0.5, 0.1, 0.1, 0.3],
                        k=1,
                    )[0]

    def _populate(self, size):
        records = super()._populate(size)
        self. _update_attendees(records)
        return records

    def _populate_factories(self):
        ORGANIZER_COUNT = 4
        PARTNER_LIST_SIZE = 20

        def generate_weekdays(iterator, *args):
            weekdays = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
            for values in iterator:
                selected_weekdays = random.choices(weekdays, k=random.randint(1, 3))
                weekday_values = {
                    d: d in selected_weekdays
                    for d in weekdays
                }
                yield {**weekday_values, **values}

        @lru_cache()
        def get_user_ids():
            group_user_id = self.env['ir.model.data']._xmlid_to_res_id('base.group_user', raise_if_not_found=False)
            return self.env['res.users'].search(
                [('groups_id', 'in', (group_user_id,))],
                order='id',
                limit=ORGANIZER_COUNT,
            ).ids

        @lru_cache()
        def get_partners_list():
            return self.env['res.partner'].search(
                [
                    ('id', 'in', self.env.registry.populated_models['res.partner']),
                    ('email', '!=', False)
                ],
                limit=PARTNER_LIST_SIZE * 10,
            ).ids

        def get_partners(random, values, **kwargs):
            return [
                (4, partner_id)
                for partner_id in random.choices(get_partners_list(), k=random.randint(1, PARTNER_LIST_SIZE))
            ]

        def get_rrule_type(values=None, random=None, **kwargs):
            if values['recurrency']:
                return random.choices(['daily', 'weekly'], weights=[0.5, 0.5], k=1)[0]
            return False

        def get_end_type(values=None, random=None, **kwargs):
            if values['recurrency']:
                return random.choices(['count', 'forever'], weights=[0.995, 0.005], k=1)[0]
            return False

        def get_count(values=None, random=None, **kwargs):
            if values['recurrency'] and values['end_type'] == 'count':
                return random.choices([3, 10, 30, 100, 300], weights=[0.24, 0.4, 0.3, 0.05, 0.01], k=1)[0]
            return False

        def get_interval(values=None, random=None, **kwargs):
            if values['recurrency']:
                return random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.4, 0.2, 0.1], k=1)[0]
            return False

        def get_name(values=None, counter=None, **kwargs):
            return f"recurring_event_{counter}" if values.get("recurrency") else f"simple_event_{counter}"

        def get_start(values=None, counter=None, **kwargs):
            return datetime.now() + timedelta(days=random.randint(0, 365))

        def get_stop(values=None, counter=None, **kwargs):
            return values['start'] + timedelta(hours=1)

        return [
            ("name", populate.compute(get_name)),
            ('active', populate.randomize([True, False], [0.9, 0.1])),
            ("user_id", populate.randomize(get_user_ids(), [0.4, 0.4, 0.1, 0.1])),
            ("start", populate.compute(get_start)),
            ("stop", populate.compute(get_stop)),
            ("partner_ids", populate.compute(get_partners)),
            ('recurrency', populate.randomize([True, False], [0.2, 0.8])),
            ('rrule_type', populate.compute(get_rrule_type)),
            ('end_type', populate.compute(get_end_type)),
            ('count', populate.compute(get_count)),
            ('interval', populate.compute(get_interval)),
            ('_weekdays', generate_weekdays),
        ]
