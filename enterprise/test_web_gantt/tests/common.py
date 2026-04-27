# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.addons.web_gantt.models.models import Base
from odoo.tests.common import TransactionCase


class TestWebGantt(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        """
            pills structure

            ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
            │ Pill 1  │ -->  │ Pill 2  │ -->  │ Pill 3  │ -->  │ Pill 4  │
            └─────────┘      └─────────┘      └─────────┘      └─────────┘
        """
        cls.TestWebGanttPill = cls.env['test.web.gantt.pill']
        cls.dependency_field_name = 'dependency_field'
        cls.dependency_inverted_field_name = 'dependency_inverted_field'
        cls.date_start_field_name = 'date_start'
        cls.date_stop_field_name = 'date_stop'
        cls.pill_1_start_date = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(weeks=2)
        cls.pill_1_stop_date = cls.pill_1_start_date + timedelta(hours=8)
        cls.pill_1 = cls.create_pill('Pill 1', cls.pill_1_start_date, cls.pill_1_stop_date)
        cls.pill_2_start_date = cls.pill_1_start_date + timedelta(days=1)
        cls.pill_2_stop_date = cls.pill_2_start_date + timedelta(hours=8)
        cls.pill_2 = cls.create_pill('Pill 2', cls.pill_2_start_date, cls.pill_2_stop_date, [cls.pill_1.id])
        cls.pill_3_start_date = cls.pill_2_start_date + timedelta(days=1)
        cls.pill_3_stop_date = cls.pill_3_start_date + timedelta(hours=8)
        cls.pill_3 = cls.create_pill('Pill 3', cls.pill_3_start_date, cls.pill_3_stop_date, [cls.pill_2.id])
        cls.pill_4_start_date = cls.pill_3_start_date + timedelta(days=1)
        cls.pill_4_stop_date = cls.pill_4_start_date + timedelta(hours=8)
        cls.pill_4 = cls.create_pill('Pill 4', cls.pill_4_start_date, cls.pill_4_stop_date, [cls.pill_3.id])
        cls.pills_topo_order = [cls.pill_1, cls.pill_2, cls.pill_3, cls.pill_4]

        """
            Second pills structure (with more nodes and use cases)

                                                             [4]->[6]
                                                                   |
             [14]     [13]                                         v
                 [11]    [12]        --->[0]->[1]->[2]       [5]->[7]->[8]-----------------
                                     |         |              |                           |
                                     |         v              v                           |
                                     |        [3]            [9]->[10]                    |
                                     |                                                    |
                                     ---------------------<x>------------------------------

            [0]->[1] means 1 blocked by 0
            <: left arrow to move task 8 backward task 0
            >: right arrow to move task 0 forward task 8
            x: delete the dependence
        """

        cls.initial_dates = {
            '0': (datetime(2024, 3, 1, 8, 0), datetime(2024, 3, 1, 12, 0)),
            '1': (datetime(2024, 3, 1, 13, 0), datetime(2024, 3, 1, 17, 0)),
            '2': (datetime(2024, 3, 4, 8, 0), datetime(2024, 3, 4, 10, 0)),
            '3': (datetime(2024, 3, 2, 11, 0), datetime(2024, 3, 2, 17, 0)),
            '4': (datetime(2024, 3, 5, 8, 0), datetime(2024, 3, 6, 17, 0)),
            '5': (datetime(2024, 3, 7, 8, 0), datetime(2024, 3, 8, 17, 0)),
            '6': (datetime(2024, 3, 9, 8, 0), datetime(2024, 3, 13, 12, 0)),
            '7': (datetime(2024, 3, 13, 13, 0), datetime(2024, 3, 13, 17, 0)),
            '8': (datetime(2024, 3, 15, 8, 0), datetime(2024, 3, 16, 14, 0)),
            '9': (datetime(2024, 3, 14, 8, 0), datetime(2024, 3, 14, 12, 0)),
            '10': (datetime(2024, 3, 14, 13, 0), datetime(2024, 3, 14, 17, 0)),
            '11': (datetime(2024, 2, 28, 8, 0), datetime(2024, 2, 28, 11, 0)),
            '12': (datetime(2024, 2, 29, 15, 0), datetime(2024, 2, 29, 16, 0)),
            '13': (datetime(2024, 2, 29, 9, 0), datetime(2024, 2, 29, 15, 0)),
            '14': (datetime(2024, 2, 26, 8, 0), datetime(2024, 2, 26, 15, 0)),
        }

        vals = []
        for name, dates in cls.initial_dates.items():
            vals.append({
                'name': name,
                cls.date_start_field_name: dates[0],
                cls.date_stop_field_name: dates[1],
            })

        cls.pills2_0, \
        cls.pills2_1, \
        cls.pills2_2, \
        cls.pills2_3, \
        cls.pills2_4, \
        cls.pills2_5, \
        cls.pills2_6, \
        cls.pills2_7, \
        cls.pills2_8, \
        cls.pills2_9, \
        cls.pills2_10, \
        cls.pills2_11, \
        cls.pills2_12, \
        cls.pills2_13, \
        cls.pills2_14 = cls.TestWebGanttPill.create(vals)

        cls.initial_dates.update({
            cls.pill_1.name: (cls.pill_1.date_start, cls.pill_1.date_stop),
            cls.pill_2.name: (cls.pill_2.date_start, cls.pill_2.date_stop),
            cls.pill_3.name: (cls.pill_3.date_start, cls.pill_3.date_stop),
            cls.pill_4.name: (cls.pill_4.date_start, cls.pill_4.date_stop),
        })

        cls.pills2_0.write({
            cls.dependency_field_name: [Command.link(cls.pills2_8.id)],
            cls.dependency_inverted_field_name: [Command.link(cls.pills2_1.id)],
        })
        cls.pills2_1.write({
            cls.dependency_inverted_field_name: [Command.link(cls.pills2_2.id), Command.link(cls.pills2_3.id)]
        })
        cls.pills2_6.write({
            cls.dependency_field_name: [Command.link(cls.pills2_4.id)],
        })
        cls.pills2_7.write({
            cls.dependency_field_name: [Command.link(cls.pills2_5.id), Command.link(cls.pills2_6.id)],
        })
        cls.pills2_8.write({
            cls.dependency_field_name: [Command.link(cls.pills2_7.id)],
        })
        cls.pills2_9.write({
            cls.dependency_field_name: [Command.link(cls.pills2_5.id)],
        })
        cls.pills2_10.write({
            cls.dependency_field_name: [Command.link(cls.pills2_9.id)],
        })

    @classmethod
    def create_pill(cls, name, date_start, date_stop, master_pill_ids=None):
        if master_pill_ids is None:
            master_pill_ids = []
        return cls.TestWebGanttPill.create({
            'name': name,
            cls.date_start_field_name: date_start,
            cls.date_stop_field_name: date_stop,
            cls.dependency_field_name: [Command.set([master_pill_id for master_pill_id in master_pill_ids])],
        })

    @classmethod
    def gantt_reschedule_forward(cls, master_record, slave_record):
        return cls.TestWebGanttPill.web_gantt_reschedule(
            Base._WEB_GANTT_RESCHEDULE_FORWARD,
            master_record.id, slave_record.id,
            cls.dependency_field_name, cls.dependency_inverted_field_name,
            cls.date_start_field_name, cls.date_stop_field_name
        )

    @classmethod
    def gantt_reschedule_backward(cls, master_record, slave_record):
        return cls.TestWebGanttPill.web_gantt_reschedule(
            Base._WEB_GANTT_RESCHEDULE_BACKWARD,
            master_record.id, slave_record.id,
            cls.dependency_field_name, cls.dependency_inverted_field_name,
            cls.date_start_field_name, cls.date_stop_field_name
        )

    def assert_not_replanned(cls, pills, initial_dates):
        for pill in pills:
            cls.assertEqual(pill[cls.date_start_field_name], initial_dates[pill.name][0], f"pill {pill.name} should not be replanned")
            cls.assertEqual(pill[cls.date_stop_field_name], initial_dates[pill.name][1], f"pill {pill.name} should not be replanned")

    def assert_old_pills_vals(cls, res, _type, message, moved_pills, initial_dates):
        cls.assertDictEqual(res, {
            'type': _type,
            'message': message,
            'old_vals_per_pill_id': {
                pill.id: {
                    'date_start': initial_dates[pill.name][0],
                    'date_stop': initial_dates[pill.name][1],
                } for pill in moved_pills
            },
        })
