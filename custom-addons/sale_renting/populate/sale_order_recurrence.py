# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class SaleOrderRecurrence(models.Model):
    _inherit = "sale.temporal.recurrence"
    _populate_sizes = {"small": 10, "medium": 30, "large": 100}

    def _populate_factories(self):

        return [
            ('name', populate.constant('recurrence_{counter}')),
            ('unit', populate.randomize(['week', 'month', 'year'], [0.2, 0.4, 0.4])),
            ('duration', populate.randomize([1, 2, 3, 4, 5], [0.2]*5)),
        ]
