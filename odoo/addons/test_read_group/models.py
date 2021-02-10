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


class Order(models.Model):
    _name = 'test_read_group.order'
    _description = 'Sales order'

    line_ids = fields.One2many('test_read_group.order.line', 'order_id')


class OrderLine(models.Model):
    _name = 'test_read_group.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('test_read_group.order', ondelete='cascade')
    value = fields.Integer()


class VirtualFields(models.Model):
    _name = 'test_read_group.adhoc'
    _description = 'Test Grouping by virtual fields'

    deadline = fields.Date('Due Date')
    tz = fields.Char('Timezone', default='UTC')
    partner_id = fields.Many2one('res.partner')
    line_ids = fields.One2many('test_read_group.adhoc.line', 'container_id')

    def _generate_adhoc_fields(self):
        res = super()._generate_adhoc_fields()

        if 'total' not in res:

            def total_sql(records, alias, query):
                coalias = self.env['test_read_group.adhoc.line']._table
                return f"""(
                    SELECT SUM("{coalias}"."packages_count" * "{coalias}"."qty")
                    FROM "{coalias}"
                    WHERE "{coalias}"."container_id" = "{alias}".id
                )"""

            res['total'] = {
                'sql': total_sql,
                'type': 'float'
            }

        if 'state' not in res:

            def state_sql(records, alias, query):
                return f"""
                    CASE
                    WHEN "{alias}".deadline - (CURRENT_DATE AT TIME ZONE "{alias}".tz)::date > 0 THEN 'planned'
                    WHEN "{alias}".deadline - (CURRENT_DATE AT TIME ZONE "{alias}".tz)::date < 0 THEN 'overdue'
                    WHEN "{alias}".deadline - (CURRENT_DATE AT TIME ZONE "{alias}".tz)::date = 0 THEN 'today'
                    ELSE null
                    END
                """

            res['state'] = {
                'sql': state_sql,
                'type': 'char'
            }

        return res


class VirtualFieldsLine(models.Model):
    _name = 'test_read_group.adhoc.line'
    _description = 'Test Grouping by virtual fields: Lines'

    container_id = fields.Many2one('test_read_group.adhoc')
    name = fields.Char()
    packages_count = fields.Integer('Number of packages')
    qty = fields.Float('Qty in a package')
