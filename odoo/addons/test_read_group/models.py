# -*- coding: utf-8 -*-
from odoo import fields, models


class GroupOnDate(models.Model):
    _name = 'test_read_group.on_date'
    _description = 'Group Test Read On Date'

    date = fields.Date("Date")
    value = fields.Integer("Value")


class BooleanAggregate(models.Model):
    _name = 'test_read_group.aggregate.boolean'
    _description = 'Group Test Read Boolean Aggregate'
    _order = 'key DESC'

    key = fields.Integer()
    bool_and = fields.Boolean(default=False, group_operator='bool_and')
    bool_or = fields.Boolean(default=False, group_operator='bool_or')
    bool_array = fields.Boolean(default=False, group_operator='array_agg')


class Aggregate(models.Model):
    _name = 'test_read_group.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    partner_id = fields.Many2one('res.partner')


class GroupOnSelection(models.Model):
    _name = 'test_read_group.on_selection'
    _description = 'Group Test Read On Selection'

    state = fields.Selection([('a', "A"), ('b', "B")], group_expand='_expand_states')
    value = fields.Integer()

    def _expand_states(self, states, domain, order):
        # return all possible states, in order
        return [key for key, val in type(self).state.selection]


class FillTemporal(models.Model):
    _name = 'test_read_group.fill_temporal'
    _description = 'Group Test Fill Temporal'

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()
