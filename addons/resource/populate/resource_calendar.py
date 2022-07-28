# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random

from odoo import models
from odoo.tools import populate
from datetime import datetime, timedelta


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"
    _populate_dependencies = ["res.company"]  # multi-company setup
    _populate_sizes = {
        "small": 10,  # 1-2 per company
        "medium": 30,  # 3 per company
        "large": 250  # 5 per company
    }

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"]

        return [
            ("company_id", populate.iterate(company_ids)),
            ("name", populate.iterate(["A little {counter}", "A lot {counter}"])),
        ]

    def _populate(self, size):
        records = super()._populate(size)

        # Randomly remove 1 half day from schedule
        a_lot = records.filtered_domain([("name", "like", "A lot")])
        for record in a_lot:
            att_id = record.attendance_ids[random.randint(0, 9)]
            record.write({
                'attendance_ids': [(3, att_id.id)],
            })

        # Randomly remove 3 to 5 half days from schedule
        a_little = records - a_lot
        for record in a_little:
            to_pop = random.sample(range(10), random.randint(3, 5))
            record.write({
                'attendance_ids': [(3, record.attendance_ids[idx].id) for idx in to_pop],
            })
        return records

class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    _populate_dependencies = ['resource.calendar']

    _populate_sizes = {
        "small": 30,
        "medium": 50,
        "large": 300
    }

    def _populate_factories(self):
        def get_calendar_id(values, counter, random):
            return random.choice(self.env['resource.calendar'].search([])).id

        def _compute_dates(iterator, field_name, model_name):
            i = 0
            while values := next(iterator, False):
                length = random.randint(1, 10)
                values['date_from'] = datetime.now() + timedelta(days=i)
                values['date_to'] = datetime.now() + timedelta(days=i+length)
                i += random.randint(length, length+10)
                yield values

        return [
            ('name', populate.constant("Leave {counter}")),
            ('_compute_dates', _compute_dates),
            ('calendar_id', populate.compute(get_calendar_id)),
            ('time_type', populate.iterate(['leave', 'other'], [0.8, 0.2]))
        ]
