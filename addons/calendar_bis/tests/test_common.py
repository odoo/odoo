# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests.common import TransactionCase


class TestCalendarCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_user_A = cls.create_user('Anya')
        cls.calendar_user_B = cls.create_user('Ben')
        cls.calendar_user_C = cls.create_user('Charlie')

        cls.CalTS = cls.env['calendar.timeslot'].with_user(cls.calendar_user_A)
        cls.CalAtt = cls.env['calendar.attendee_bis'].with_user(cls.calendar_user_A)

        default_values = {
            'partner_id': cls.calendar_user_A.partner_id.id,
            'description': 'DESCRIPTION',
        }

        cls.single_event = cls.create_event({**default_values, 'name': 'EVENT 1', 'start': datetime(2024, 1, 1, 10, 0), 'stop': datetime(2024, 1, 1, 11, 0)})
        cls.add_attendee(cls.single_event, cls.calendar_user_B)
        cls.public_event = cls.create_event({**default_values, 'name': 'PUBLIC EVENT', 'start': datetime(2024, 1, 3, 15, 0), 'stop': datetime(2024, 1, 3, 16, 0), 'is_public': True})
        cls.add_attendee(cls.public_event, cls.calendar_user_B)

    @classmethod
    def create_event(cls, values):
        return cls.CalTS.create(values)

    @classmethod
    def create_user(cls, name):
        return cls.env['res.users'].create({
            'name': name,
            'login': name,
            'password': name,
            'email': name + '@test.calendar',
        })

    @classmethod
    def add_attendee(cls, event, user):
        return cls.CalAtt.create({
            'timeslot_id': event.id,
            'partner_id': user.partner_id.id,
            'state': 'yes',
        })
