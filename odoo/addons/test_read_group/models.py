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
        return [key for key, val in type(self).state.selection]


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


class Related1(models.Model):
    _name = 'test_read_group.related1'
    _description = 'related1'

    partner_id = fields.Many2one('res.partner', required=True)
    country_code = fields.Char(related='partner_id.country_id.code')


class Related2(models.Model):
    _name = 'test_read_group.related2'
    _inherits = {'test_read_group.related1': 'related1_id'}
    _description = 'related2'

    related1_id = fields.Many2one('test_read_group.related1', required=True, ondelete='cascade')
    state_id = fields.Many2one('res.country.state', related='partner_id.state_id')
    state_stored_id = fields.Many2one('res.country.state', related='partner_id.state_id', store=True, string='State (stored)')
    country_code2 = fields.Char(related='partner_id.country_id.code', string='Country Code 2')
    partner_city = fields.Char(related='partner_id.city')


# auto_join is True for delegate fields
# See https://github.com/odoo/odoo/commit/22b0142d4e9d72b80f50388d17ebf3e95d76deba
class Related3(models.Model):
    _name = 'test_read_group.related3'
    _inherits = {'test_read_group.related2': 'related2_id'}
    _description = 'related3 (compute_sudo=True, auto_join=True)'

    related2_id = fields.Many2one('test_read_group.related2', required=True, ondelete='cascade')
    state_code = fields.Char(related='partner_id.state_id.code', string='State Code')
    state_code2 = fields.Char(related='state_id.code', string='State Code2')
    state_stored_code = fields.Char(related='state_stored_id.code', string='State Code (stored)')


class Related3NoSudo(models.Model):
    _name = 'test_read_group.related3.nosudo'
    _inherits = {'test_read_group.related2': 'related2_id'}
    _description = 'related3 (compute_sudo=False, auto_join=True)'

    related2_id = fields.Many2one('test_read_group.related2', required=True, ondelete='cascade')
    state_code = fields.Char(related='partner_id.state_id.code', string='State Code', compute_sudo=False)
    state_code2 = fields.Char(related='state_id.code', string='State Code2', compute_sudo=False)
    state_stored_code = fields.Char(related='state_stored_id.code', string='State Code (stored)', compute_sudo=False)


class Related3NoSudoNoDelegate(models.Model):
    _name = 'test_read_group.related3.nosudo.nodelegate'
    _description = 'related3 (compute_sudo=False, auto_join=False, delegate=False)'

    related2_id = fields.Many2one('test_read_group.related2', required=True, ondelete='cascade')
    state_code = fields.Char(related='related2_id.partner_id.state_id.code', string='State Code', compute_sudo=False)
    state_code2 = fields.Char(related='related2_id.state_id.code', string='State Code2', compute_sudo=False)
    state_stored_code = fields.Char(related='related2_id.state_stored_id.code', string='State Code (stored)', compute_sudo=False)
