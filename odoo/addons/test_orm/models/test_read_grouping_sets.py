from odoo import api, fields, models


class Test_Read_Grouping_Sets_Aggregate(models.Model):
    _name = 'read_grouping_sets.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one('res.partner')
    display_name = fields.Char(store=True)


class Test_Read_Grouping_Sets_User(models.Model):
    _name = 'read_grouping_sets.user'
    _description = "User"

    name = fields.Char(required=True)
    task_ids = fields.Many2many(
        'read_grouping_sets.task',
        'read_grouping_sets_task_user_rel',
        'user_id',
        'task_id',
        string="Tasks",
    )


class Test_Read_Grouping_Sets_Task(models.Model):
    _name = 'read_grouping_sets.task'
    _description = "Project task"

    name = fields.Char(required=True)
    user_ids = fields.Many2many(
        'read_grouping_sets.user',
        'read_grouping_sets_task_user_rel',
        'task_id',
        'user_id',
        string="Collaborators",
    )
    customer_ids = fields.Many2many(
        'read_grouping_sets.user',
        'read_grouping_sets_task_user_rel_2',
        'task_id',
        'user_id',
        string="Customers",
    )
    tag_ids = fields.Many2many(
        'read_grouping_sets.tag',
        'read_grouping_sets_task_tag_rel',
        'task_id',
        'tag_id',
        string="Tags",
    )
    active_tag_ids = fields.Many2many(
        'read_grouping_sets.tag',
        'read_grouping_sets_task_tag_rel',
        'task_id',
        'tag_id',
        string="Active Tags",
        domain=[('active', '=', True)],
    )
    all_tag_ids = fields.Many2many(
        'read_grouping_sets.tag',
        'read_grouping_sets_task_tag_rel',
        'task_id',
        'tag_id',
        string="All Tags",
        context={'active_test': False},
    )
    date = fields.Date()
    integer = fields.Integer()
    key = fields.Char()


class Test_Read_Grouping_Sets_Tag(models.Model):
    _name = 'read_grouping_sets.tag'
    _description = "Project tag"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class Test_Read_Grouping_SetsRelated_Bar(models.Model):
    _name = 'read_grouping_sets.r_bar'
    _description = "RelatedBar"

    name = fields.Char(aggregator="count_distinct")

    foo_ids = fields.One2many('read_grouping_sets.r_foo', 'bar_id')
    foo_names_sudo = fields.Char('name_one2many_related', related='foo_ids.name')

    base_ids = fields.Many2many('read_grouping_sets.r_base')
    computed_base_ids = fields.Many2many('read_grouping_sets.r_base', compute='_compute_computed_base_ids')

    def _compute_computed_base_ids(self):
        self.computed_base_ids = False


class Test_Read_Grouping_SetsRelated_Foo(models.Model):
    _name = 'read_grouping_sets.r_foo'
    _description = "RelatedFoo"

    name = fields.Char()
    bar_id = fields.Many2one('read_grouping_sets.r_bar')

    bar_name_sudo = fields.Char('bar_name_sudo', related='bar_id.name')
    bar_name = fields.Char('bar_name', related='bar_id.name', related_sudo=False)

    bar_base_ids = fields.Many2many(related='bar_id.base_ids')

    schedule_datetime = fields.Datetime()


class Test_Read_Grouping_SetsRelated_Base(models.Model):
    _name = 'read_grouping_sets.r_base'
    _description = "RelatedBase"

    name = fields.Char()
    value = fields.Integer()
    foo_id = fields.Many2one('read_grouping_sets.r_foo')

    foo_id_name = fields.Char("foo_id_name", related='foo_id.name', related_sudo=False)
    foo_id_name_sudo = fields.Char("foo_id_name_sudo", related='foo_id.name')

    foo_id_bar_id_name = fields.Char('foo_bar_name_sudo', related='foo_id.bar_id.name')
    foo_id_bar_name = fields.Char('foo_bar_name_sudo_1', related='foo_id.bar_name')
    foo_id_bar_name_sudo = fields.Char('foo_bar_name_sudo_2', related='foo_id.bar_name_sudo')


class Test_Read_Grouping_SetsRelated_Inherits(models.Model):
    _name = 'read_grouping_sets.r_inherits'
    _description = "RelatedInherits"
    _inherits = {
        'read_grouping_sets.r_base': 'base_id',
    }

    base_id = fields.Many2one('read_grouping_sets.r_base', required=True, ondelete='cascade')


class Test_Read_Grouping_SetsChain_Inherits(models.Model):
    _name = 'read_grouping_sets.chain_inherits'
    _description = "ChainInherits"

    inherited_id = fields.Many2one('read_grouping_sets.r_inherits', required=True)
