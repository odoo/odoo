# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import populate


class PlanningSlot(models.Model):
    _inherit = "planning.slot"
    _populate_sizes = {"small": 500, "medium": 5000, "large": 50000}
    _populate_dependencies = ["hr.employee", "res.company", 'planning.role', 'planning.slot.template']

    def _populate_factories(self):
        employee_ids = self.env.registry.populated_models["hr.employee"]
        role_ids = self.env.registry.populated_models["planning.role"]

        def get_resource_id(values=None, random=None, **kwargs):
            return random.choice(self.env['hr.employee'].browse(values['employee_id']).resource_id.ids)

        def get_start_datetime(counter, **kwargs):
            date_from = datetime.datetime.now().replace(hour=0, minute=0, second=0)\
                + relativedelta(days=int(3 * int(counter)))
            return date_from

        def get_end_datetime(counter, random=None, **kwargs):
            date_to = datetime.datetime.now().replace(hour=23, minute=59, second=59)\
                + relativedelta(days=int(3 * int(counter)) + random.randint(0, 2))
            return date_to

        return [
            ('name', populate.constant('shift_{counter}')),
            ('start_datetime', populate.compute(get_start_datetime)),
            ('end_datetime', populate.compute(get_end_datetime)),
            ('employee_id', populate.randomize(employee_ids)),
            ('resource_id', populate.compute(get_resource_id)),
            ('role_id', populate.randomize(role_ids)),
        ]
