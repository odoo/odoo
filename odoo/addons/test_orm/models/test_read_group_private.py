from odoo import fields, models


class Test_Read_Group_Private_AggregateBoolean(models.Model):
    _name = 'read_group_private.aggregate.boolean'
    _description = 'Group Test Read Boolean Aggregate'
    _order = 'key DESC'

    key = fields.Integer()
    bool_and = fields.Boolean(default=False, aggregator='bool_and')
    bool_or = fields.Boolean(default=False, aggregator='bool_or')
    bool_array = fields.Boolean(default=False, aggregator='array_agg')


class Test_Read_Group_Private_Aggregate(models.Model):
    _name = 'read_group_private.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one('res.partner')
    display_name = fields.Char(store=True)


class Test_Read_Group_Private_Fill_Temporal(models.Model):
    _name = 'read_group_private.fill_temporal'
    _description = 'Group Test Fill Temporal'

    date = fields.Date()
    datetime = fields.Datetime()
    value = fields.Integer()


class Test_Read_Group_Private_Order(models.Model):
    _name = 'read_group_private.order'
    _description = 'Sales order'

    line_ids = fields.One2many('read_group_private.order.line', 'order_id')
    date = fields.Date()
    company_dependent_name = fields.Char(company_dependent=True)
    many2one_id = fields.Many2one('read_group_private.order')
    name = fields.Char()
    fold = fields.Boolean()

    @property
    def _order(self):
        if self.env.context.get('read_group_private_order_company_dependent'):
            return 'company_dependent_name'
        return super()._order


class Test_Read_Group_Private_OrderLine(models.Model):
    _name = 'read_group_private.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('read_group_private.order')
    order_expand_id = fields.Many2one('read_group_private.order', group_expand='_read_group_expand_full')
    value = fields.Integer()
    date = fields.Date(related='order_id.date')


class Test_Read_Group_Private_User(models.Model):
    _name = 'read_group_private.user'
    _description = "User"

    name = fields.Char(required=True)
    task_ids = fields.Many2many(
        'read_group_private.task',
        'read_group_private_task_user_rel',
        'user_id',
        'task_id',
        string="Tasks",
    )


class Test_Read_Group_Private_Task(models.Model):
    _name = 'read_group_private.task'
    _description = "Project task"

    name = fields.Char(required=True)
    user_ids = fields.Many2many(
        'read_group_private.user',
        'read_group_private_task_user_rel',
        'task_id',
        'user_id',
        string="Collaborators",
    )
    customer_ids = fields.Many2many(
        'read_group_private.user',
        'read_group_private_task_user_rel_2',
        'task_id',
        'user_id',
        string="Customers",
    )
    tag_ids = fields.Many2many(
        'read_group_private.tag',
        'read_group_private_task_tag_rel',
        'task_id',
        'tag_id',
        string="Tags",
    )
    active_tag_ids = fields.Many2many(
        'read_group_private.tag',
        'read_group_private_task_tag_rel',
        'task_id',
        'tag_id',
        string="Active Tags",
        domain=[('active', '=', True)],
    )
    all_tag_ids = fields.Many2many(
        'read_group_private.tag',
        'read_group_private_task_tag_rel',
        'task_id',
        'tag_id',
        string="All Tags",
        context={'active_test': False},
    )
    date = fields.Date()
    integer = fields.Integer()
    key = fields.Char()


class Test_Read_Group_Private_Tag(models.Model):
    _name = 'read_group_private.tag'
    _description = "Project tag"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class Test_Read_Group_Private_Related_Bar(models.Model):
    _name = 'read_group_private.r_bar'
    _description = "RelatedBar"

    name = fields.Char(aggregator="count_distinct")

    foo_ids = fields.One2many('read_group_private.r_foo', 'bar_id')
    foo_names_sudo = fields.Char('name_one2many_related', related='foo_ids.name')

    base_ids = fields.Many2many('read_group_private.related_base')
    computed_base_ids = fields.Many2many('read_group_private.related_base', compute='_compute_computed_base_ids')

    def _compute_computed_base_ids(self):
        self.computed_base_ids = False


class Test_Read_Group_Private_Related_Foo(models.Model):
    _name = 'read_group_private.r_foo'
    _description = "RelatedFoo"

    name = fields.Char()
    bar_id = fields.Many2one('read_group_private.r_bar')

    bar_name_sudo = fields.Char('bar_name_sudo', related='bar_id.name')
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)

    bar_base_ids = fields.Many2many(related='bar_id.base_ids')

    schedule_datetime = fields.Datetime()


class Test_Read_Group_Private_Related_Base(models.Model):
    _name = 'read_group_private.related_base'
    _description = "RelatedBase"

    name = fields.Char()
    value = fields.Integer()
    foo_id = fields.Many2one('read_group_private.r_foo')

    foo_id_name = fields.Char("foo_id_name", related='foo_id.name', related_sudo=False)
    foo_id_name_sudo = fields.Char("foo_id_name_sudo", related='foo_id.name')

    foo_id_bar_id_name = fields.Char('foo_bar_name_sudo', related='foo_id.bar_id.name')
    foo_id_bar_name = fields.Char('foo_bar_name_sudo_1', related='foo_id.bar_name')
    foo_id_bar_name_sudo = fields.Char('foo_bar_name_sudo_2', related='foo_id.bar_name_sudo')


class Test_Read_Group_Private_Related_Inherits(models.Model):
    _name = 'read_group_private.related_inherits'
    _description = "RelatedInherits"
    _inherits = {
        'read_group_private.related_base': 'base_id',
    }

    base_id = fields.Many2one('read_group_private.related_base', required=True, ondelete='cascade')
    