from odoo import api, fields, models


class TestReadGroupPrivateAggregate(models.Model):
    _name = 'test_read_group_private.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one('res.partner')
    display_name = fields.Char(store=True)


class TestReadGroupPrivateAggregateBoolean(models.Model):
    _name = 'test_read_group_private.aggregate.boolean'
    _description = 'Group Test Read Boolean Aggregate'
    _order = 'key DESC'

    key = fields.Integer()
    bool_and = fields.Boolean(default=False, aggregator='bool_and')
    bool_or = fields.Boolean(default=False, aggregator='bool_or')
    bool_array = fields.Boolean(default=False, aggregator='array_agg')


class TestReadGroupPrivateOrder(models.Model):
    _name = 'test_read_group_private.order'
    _description = 'Sales order'

    line_ids = fields.One2many('test_read_group_private.order.line', 'order_id')


class TestReadGroupPrivateOrderLine(models.Model):
    _name = 'test_read_group_private.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('test_read_group_private.order')
    value = fields.Integer()


class TestReadGroupPrivateFillTemporal(models.Model):
    _name = 'test_read_group_private.fill_temporal'
    _description = 'Group Test Fill Temporal'

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()


class TestReadGroupPrivateUser(models.Model):
    _name = 'test_read_group_private.user'
    _description = "User"

    name = fields.Char(required=True)
    task_ids = fields.Many2many(
        'test_read_group_private.task',
        'test_read_group_private_task_user_rel',
        'user_id',
        'task_id',
        string="Tasks",
    )


class TestReadGroupPrivateTask(models.Model):
    _name = 'test_read_group_private.task'
    _description = "Project task"

    name = fields.Char(required=True)
    user_ids = fields.Many2many(
        'test_read_group_private.user',
        'test_read_group_private_task_user_rel',
        'task_id',
        'user_id',
        string="Collaborators",
    )
    tag_ids = fields.Many2many(
        'test_read_group_private.tag',
        'test_read_group_private_task_tag_rel',
        'task_id',
        'tag_id',
        string="Tags",
    )
    active_tag_ids = fields.Many2many(
        'test_read_group_private.tag',
        'test_read_group_private_task_tag_rel',
        'task_id',
        'tag_id',
        string="Active Tags",
        domain=[('active', '=', True)],
    )
    all_tag_ids = fields.Many2many(
        'test_read_group_private.tag',
        'test_read_group_private_task_tag_rel',
        'task_id',
        'tag_id',
        string="All Tags",
        context={'active_test': False},
    )


class TestReadGroupPrivateTag(models.Model):
    _name = 'test_read_group_private.tag'
    _description = "Project tag"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class TestReadGroupPrivateRelatedBar(models.Model):
    _name = 'test_read_group_private.related_bar'
    _description = "RelatedBar"

    name = fields.Char(aggregator="count_distinct")

    foo_ids = fields.One2many('test_read_group_private.related_foo', 'bar_id')
    foo_names_sudo = fields.Char('name_one2many_related', related='foo_ids.name')

    base_ids = fields.Many2many('test_read_group_private.related_base', relation='trgp_related_bar_trgp_related_base_rel')
    computed_base_ids = fields.Many2many('test_read_group_private.related_base', compute='_compute_computed_base_ids')

    def _compute_computed_base_ids(self):
        self.computed_base_ids = False


class TestReadGroupPrivateRelatedFoo(models.Model):
    _name = 'test_read_group_private.related_foo'
    _description = "RelatedFoo"

    name = fields.Char()
    bar_id = fields.Many2one('test_read_group_private.related_bar')

    bar_name_sudo = fields.Char('bar_name_sudo', related='bar_id.name')
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)

    bar_base_ids = fields.Many2many(related='bar_id.base_ids')


class TestReadGroupPrivateRelatedBase(models.Model):
    _name = 'test_read_group_private.related_base'
    _description = "RelatedBase"

    name = fields.Char()
    value = fields.Integer()
    foo_id = fields.Many2one('test_read_group_private.related_foo')

    foo_id_name = fields.Char("foo_id_name", related='foo_id.name', related_sudo=False)
    foo_id_name_sudo = fields.Char("foo_id_name_sudo", related='foo_id.name')

    foo_id_bar_id_name = fields.Char('foo_bar_name_sudo', related='foo_id.bar_id.name')
    foo_id_bar_name = fields.Char('foo_bar_name_sudo_1', related='foo_id.bar_name')
    foo_id_bar_name_sudo = fields.Char('foo_bar_name_sudo_2', related='foo_id.bar_name_sudo')


class TestReadGroupPrivateRelatedInherits(models.Model):
    _name = 'test_read_group_private.related_inherits'
    _description = "RelatedInherits"
    _inherits = {
        'test_read_group_private.related_base': 'base_id',
    }

    base_id = fields.Many2one('test_read_group_private.related_base', required=True, ondelete='cascade')
