# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random

from odoo import models
from odoo.tools import populate


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
