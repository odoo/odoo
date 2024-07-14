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
