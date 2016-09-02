# -*- coding: utf-8 -*-
from odoo import fields, models


class GroupOnDate(models.Model):
    _name = 'test_read_group.on_date'

    date = fields.Date("Date")
    value = fields.Integer("Value")

class BooleanAggregate(models.Model):
    _name = 'test_read_group.aggregate.boolean'
    _order = 'key DESC'

    key = fields.Integer()
    bool_and = fields.Boolean(default=False, group_operator='bool_and')
    bool_or = fields.Boolean(default=False, group_operator='bool_or')
    bool_array = fields.Boolean(default=False, group_operator='array_agg')
