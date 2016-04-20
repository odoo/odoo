# -*- coding: utf-8 -*-
from openerp import fields, models


class GroupOnDate(models.Model):
    _name = 'test_read_group.on_date'

    date = fields.Date("Date")
    value = fields.Integer("Value")
