# -*- coding: utf-8 -*-
from odoo.addons import base
from odoo import fields, models


class TestReadGroupOnDate(models.Model):
    _name = 'test_read_group.on_date'
    _description = 'Group Test Read On Date'

    date = fields.Date("Date")
    value = fields.Integer("Value")


class TestReadGroupAggregateBoolean(models.Model):
    _name = 'test_read_group.aggregate.boolean'
    _description = 'Group Test Read Boolean Aggregate'
    _order = 'key DESC'

    key = fields.Integer()
    bool_and = fields.Boolean(default=False, aggregator='bool_and')
    bool_or = fields.Boolean(default=False, aggregator='bool_or')
    bool_array = fields.Boolean(default=False, aggregator='array_agg')


class TestReadGroupAggregate(models.Model):
    _name = 'test_read_group.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one('res.partner')
    display_name = fields.Char()


# we use a selection that is in reverse lexical order, in order to check the
# possible reordering made by read_group on selection fields
SELECTION = [('c', "C"), ('b', "B"), ('a', "A")]


class TestReadGroupOnSelection(models.Model):
    _name = 'test_read_group.on_selection'
    _description = 'Group Test Read On Selection'

    state = fields.Selection([('a', "A"), ('b', "B")], group_expand='_expand_states')
    static_expand = fields.Selection(SELECTION, group_expand=True)
    dynamic_expand = fields.Selection(lambda self: SELECTION, group_expand=True)
    no_expand = fields.Selection(SELECTION)
    value = fields.Integer()

    def _expand_states(self, states, domain):
        # return all possible states, in order
        return [key for key, val in self._fields['state'].selection]


class TestReadGroupFillTemporal(models.Model):
    _name = 'test_read_group.fill_temporal'
    _description = 'Group Test Fill Temporal'

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()


class TestReadGroupOrder(models.Model):
    _name = 'test_read_group.order'
    _description = 'Sales order'

    line_ids = fields.One2many('test_read_group.order.line', 'order_id')
    date = fields.Date()


class TestReadGroupOrderLine(models.Model):
    _name = 'test_read_group.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('test_read_group.order', ondelete='cascade')
    value = fields.Integer()
    date = fields.Date(related='order_id.date')


class TestReadGroupUser(models.Model):
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


class TestReadGroupTask(models.Model):
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
    date = fields.Date()


class ResPartner(models.Model, base.ResPartner):

    date = fields.Date()


class TestReadGroupRelatedBar(models.Model):
    _name = 'test_read_group.related_bar'
    _description = "RelatedBar"

    name = fields.Char(aggregator="count_distinct")

    foo_ids = fields.One2many('test_read_group.related_foo', 'bar_id')
    foo_names_sudo = fields.Char('name_one2many_related', related='foo_ids.name')

    base_ids = fields.Many2many('test_read_group.related_base')
    computed_base_ids = fields.Many2many('test_read_group.related_base', compute='_compute_computed_base_ids')

    def _compute_computed_base_ids(self):
        self.computed_base_ids = False


class TestReadGroupRelatedFoo(models.Model):
    _name = 'test_read_group.related_foo'
    _description = "RelatedFoo"

    name = fields.Char()
    bar_id = fields.Many2one('test_read_group.related_bar')

    bar_name_sudo = fields.Char('bar_name_sudo', related='bar_id.name')
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)

    bar_base_ids = fields.Many2many('bar_name', related='bar_id.base_ids')


class TestReadGroupRelatedBase(models.Model):
    _name = 'test_read_group.related_base'
    _description = "RelatedBase"

    name = fields.Char()
    value = fields.Integer()
    foo_id = fields.Many2one('test_read_group.related_foo')

    foo_id_name = fields.Char("foo_id_name", related='foo_id.name', related_sudo=False)
    foo_id_name_sudo = fields.Char("foo_id_name_sudo", related='foo_id.name')

    foo_id_bar_id_name = fields.Char('foo_bar_name_sudo', related='foo_id.bar_id.name')
    foo_id_bar_name = fields.Char('foo_bar_name_sudo_1', related='foo_id.bar_name')
    foo_id_bar_name_sudo = fields.Char('foo_bar_name_sudo_2', related='foo_id.bar_name_sudo')


class TestReadGroupRelatedInherits(models.Model):
    _name = 'test_read_group.related_inherits'
    _description = "RelatedInherits"
    _inherits = {
        'test_read_group.related_base': 'base_id',
    }

    base_id = fields.Many2one('test_read_group.related_base', required=True, ondelete='cascade')
