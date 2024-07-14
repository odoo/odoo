# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import populate


class ProjectTask(models.Model):
    _inherit = "project.task"

    def _populate_factories(self):
        res = super()._populate_factories()
        def get_planned_date_begin(random, counter, **kwargs):
            date_from = datetime.now().replace(hour=0, minute=0, second=0)\
                + relativedelta(days=int(3 * int(counter)))
            return date_from

        def get_date_deadline(random, counter, **kwargs):
            date_to = datetime.now().replace(hour=23, minute=59, second=59)\
                + relativedelta(days=int(3 * int(counter))  + random.randint(0, 2))
            return date_to

        res += [
            ('planned_date_begin', populate.compute(get_planned_date_begin)),
            ('date_deadline', populate.compute(get_date_deadline)),
        ]
        return res
