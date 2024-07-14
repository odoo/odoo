# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import MO

from odoo.tests import HttpCase


class TestUiCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_thibault = cls.env['hr.employee'].create({
            'name': 'Aaron',
            'work_email': 'aaron@a.be',
            'tz': 'UTC',
            'employee_type': 'freelance',
            'resource_calendar_id': False,
        })
        start = datetime.now() + relativedelta(weekday=MO(-1), hour=10, minute=0, second=0, microsecond=0)
        cls.env['planning.slot'].create({
            'start_datetime': start,
            'end_datetime': start + relativedelta(hour=11),
        })
