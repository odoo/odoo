from odoo import api, fields, models


class TestReadGroupingSetsAggregate(models.Model):
    _name = 'test_read_grouping_sets.aggregate'
    _order = 'id'
    _description = 'Group Test Aggregate'

    key = fields.Integer()
    value = fields.Integer("Value")
    numeric_value = fields.Float(digits=(4, 2))
    partner_id = fields.Many2one('res.partner')
    display_name = fields.Char(store=True)


class TestReadGroupingSetsUser(models.Model):
    _name = 'test_read_grouping_sets.user'
    _description = "User"

    name = fields.Char(required=True)
    task_ids = fields.Many2many(
        'test_read_grouping_sets.task',
        'test_read_grouping_sets_task_user_rel',
        'user_id',
        'task_id',
        string="Tasks",
    )


class TestReadGroupingSetsTask(models.Model):
    _name = 'test_read_grouping_sets.task'
    _description = "Project task"

    name = fields.Char(required=True)
    user_ids = fields.Many2many(
        'test_read_grouping_sets.user',
        'test_read_grouping_sets_task_user_rel',
        'task_id',
        'user_id',
        string="Collaborators",
    )
    customer_ids = fields.Many2many(
        'test_read_grouping_sets.user',
        'test_read_grouping_sets_task_user_rel_2',
        'task_id',
        'user_id',
        string="Customers",
    )
    tag_ids = fields.Many2many(
        'test_read_grouping_sets.tag',
        'test_read_grouping_sets_task_tag_rel',
        'task_id',
        'tag_id',
        string="Tags",
    )
    active_tag_ids = fields.Many2many(
        'test_read_grouping_sets.tag',
        'test_read_grouping_sets_task_tag_rel',
        'task_id',
        'tag_id',
        string="Active Tags",
        domain=[('active', '=', True)],
    )
    all_tag_ids = fields.Many2many(
        'test_read_grouping_sets.tag',
        'test_read_grouping_sets_task_tag_rel',
        'task_id',
        'tag_id',
        string="All Tags",
        context={'active_test': False},
    )
    date = fields.Date()
    integer = fields.Integer()
    key = fields.Char()


class TestReadGroupingSetsTag(models.Model):
    _name = 'test_read_grouping_sets.tag'
    _description = "Project tag"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)