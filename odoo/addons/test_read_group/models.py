# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Test_Read_GroupOn_Date(models.Model):
    _name = 'test_read_group.on_date'
    _description = 'Group Test Read On Date'

    date = fields.Date("Date")
    value = fields.Integer("Value")


class Test_Read_GroupAggregateBoolean(models.Model):
    _name = 'test_read_group.aggregate.boolean'
    _description = 'Group Test Read Boolean Aggregate'
    _order = 'key DESC'

    key = fields.Integer()
    bool_and = fields.Boolean(default=False, aggregator='bool_and')
    bool_or = fields.Boolean(default=False, aggregator='bool_or')
    bool_array = fields.Boolean(default=False, aggregator='array_agg')


class TestReadGroupAggregateMonetaryRelated(models.Model):
    _name = 'test_read_group.aggregate.monetary.related'
    _description = 'To test related currency fields in Monetary aggregates'

    stored_currency_id = fields.Many2one('res.currency')
    non_stored_currency_id = fields.Many2one(
        'res.currency',
        compute="_compute_non_stored_currency_id",
        store=False,
    )

    @api.depends()
    def _compute_non_stored_currency_id(self):
        for record in self:
            record.non_stored_currency_id = self.env.ref('base.EUR')


class Test_Read_GroupAggregateMonetary(models.Model):
    _name = 'test_read_group.aggregate.monetary'
    _description = 'Group Test Read Monetary Aggregate'

    name = fields.Char()
    related_model_id = fields.Many2one('test_read_group.aggregate.monetary.related')

    currency_id = fields.Many2one('res.currency')
    related_stored_currency_id = fields.Many2one(
        related='related_model_id.stored_currency_id',
    )
    related_non_stored_currency_id = fields.Many2one(
        related='related_model_id.non_stored_currency_id',
    )

    total_in_currency_id = fields.Monetary(currency_field='currency_id')
    total_in_related_stored_currency_id = fields.Monetary(currency_field='related_stored_currency_id')
    total_in_related_non_stored_currency_id = fields.Monetary(currency_field='related_non_stored_currency_id')


class Test_Read_GroupAggregate(models.Model):
    _name = 'test_read_group.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one('res.partner')
    display_name = fields.Char(store=True)


# we use a selection that is in reverse lexical order, in order to check the
# possible reordering made by read_group on selection fields
SELECTION = [('c', "C"), ('b', "B"), ('a', "A")]


class Test_Read_GroupOn_Selection(models.Model):
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


class Test_Read_GroupFill_Temporal(models.Model):
    _name = 'test_read_group.fill_temporal'
    _description = 'Group Test Fill Temporal'

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()


class Test_Read_GroupOrder(models.Model):
    _name = 'test_read_group.order'
    _description = 'Sales order'

    line_ids = fields.One2many('test_read_group.order.line', 'order_id')
    date = fields.Date()
    company_dependent_name = fields.Char(company_dependent=True)
    many2one_id = fields.Many2one('test_read_group.order')
    name = fields.Char()
    fold = fields.Boolean()

    @property
    def _order(self):
        if self.env.context.get('test_read_group_order_company_dependent'):
            return 'company_dependent_name'
        return super()._order


class Test_Read_GroupOrderLine(models.Model):
    _name = 'test_read_group.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('test_read_group.order')
    order_expand_id = fields.Many2one('test_read_group.order', group_expand='_read_group_expand_full')
    value = fields.Integer()
    date = fields.Date(related='order_id.date')


class Test_Read_GroupUser(models.Model):
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


class Test_Read_GroupTask(models.Model):
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
    customer_ids = fields.Many2many(
        'test_read_group.user',
        'test_read_group_task_user_rel_2',
        'task_id',
        'user_id',
        string="Customers",
    )
    tag_ids = fields.Many2many(
        'test_read_group.tag',
        'test_read_group_task_tag_rel',
        'task_id',
        'tag_id',
        string="Tags",
    )
    active_tag_ids = fields.Many2many(
        'test_read_group.tag',
        'test_read_group_task_tag_rel',
        'task_id',
        'tag_id',
        string="Active Tags",
        domain=[('active', '=', True)],
    )
    all_tag_ids = fields.Many2many(
        'test_read_group.tag',
        'test_read_group_task_tag_rel',
        'task_id',
        'tag_id',
        string="All Tags",
        context={'active_test': False},
    )
    date = fields.Date()
    integer = fields.Integer()
    key = fields.Char()


class Test_Read_GroupTag(models.Model):
    _name = 'test_read_group.tag'
    _description = "Project tag"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    date = fields.Date()


class Test_Read_GroupRelated_Bar(models.Model):
    _name = 'test_read_group.related_bar'
    _description = "RelatedBar"

    name = fields.Char(aggregator="count_distinct")

    foo_ids = fields.One2many('test_read_group.related_foo', 'bar_id')
    foo_names_sudo = fields.Char('name_one2many_related', related='foo_ids.name')

    base_ids = fields.Many2many('test_read_group.related_base')
    computed_base_ids = fields.Many2many('test_read_group.related_base', compute='_compute_computed_base_ids')

    def _compute_computed_base_ids(self):
        self.computed_base_ids = False


class Test_Read_GroupRelated_Foo(models.Model):
    _name = 'test_read_group.related_foo'
    _description = "RelatedFoo"

    name = fields.Char()
    bar_id = fields.Many2one('test_read_group.related_bar')

    bar_name_sudo = fields.Char('bar_name_sudo', related='bar_id.name')
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)

    bar_base_ids = fields.Many2many(related='bar_id.base_ids')

    schedule_datetime = fields.Datetime()


class Test_Read_GroupRelated_Base(models.Model):
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


class Test_Read_GroupRelated_Inherits(models.Model):
    _name = 'test_read_group.related_inherits'
    _description = "RelatedInherits"
    _inherits = {
        'test_read_group.related_base': 'base_id',
    }

    base_id = fields.Many2one('test_read_group.related_base', required=True, ondelete='cascade')


class Test_Read_GroupChain_Inherits(models.Model):
    _name = 'test_read_group.chain_inherits'
    _description = "ChainInherits"

    inherited_id = fields.Many2one('test_read_group.related_inherits', required=True)
