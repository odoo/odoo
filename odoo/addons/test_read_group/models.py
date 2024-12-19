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

class MonetaryAggregate(models.Model):
    _name = 'test_read_group.aggregate.monetary'
    _description = 'Group Test Aggregate for Monetary Field'

    currency_id = fields.Many2one('res.currency')
    key = fields.Integer()
    amount = fields.Monetary()

# we use a selection that is in reverse lexical order, in order to check the
# possible reordering made by read_group on selection fields
SELECTION = [('c', "C"), ('b', "B"), ('a', "A")]


class GroupOnSelection(models.Model):
    _name = 'test_read_group.on_selection'
    _description = 'Group Test Read On Selection'

    state = fields.Selection([('a', "A"), ('b', "B")], group_expand='_expand_states')
    static_expand = fields.Selection(SELECTION, group_expand=True)
    dynamic_expand = fields.Selection(lambda self: SELECTION, group_expand=True)
    no_expand = fields.Selection(SELECTION)
    value = fields.Integer()

    def _expand_states(self, states, domain, order):
        # return all possible states, in order
        return [key for key, val in self._fields['state'].selection]


class FillTemporal(models.Model):
    _name = 'test_read_group.fill_temporal'
    _description = 'Group Test Fill Temporal'

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()


class Order(models.Model):
    _name = 'test_read_group.order'
    _description = 'Sales order'

    line_ids = fields.One2many('test_read_group.order.line', 'order_id')


class OrderLine(models.Model):
    _name = 'test_read_group.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('test_read_group.order', ondelete='cascade')
    value = fields.Integer()


class User(models.Model):
    _name = 'test_read_group.user'
    _description = "User"

    name = fields.Char(required=True)
    task_ids = fields.Many2many(
        'test_read_group.task',
        'test_read_group_task_user_rel',
        'user_id',
        'task_id',
        string="Tasks",
    )


class Task(models.Model):
    _name = 'test_read_group.task'
    _description = "Project task"

    name = fields.Char(required=True)
    user_ids = fields.Many2many(
        'test_read_group.user',
        'test_read_group_task_user_rel',
        'task_id',
        'user_id',
        string="Collaborators",
    )
