from psycopg2.errors import GroupingError

from odoo import models
from odoo.tests.common import tagged, TransactionCase


@tagged('-at_install', 'post_install')
class TestReadGroupOverride(TransactionCase):
    def test_order_for_groupby(self):
        Order = self.env['test_read_group.order']
        many2one_field = Order._fields['many2one_id']
        self.addCleanup(setattr, many2one_field, 'comodel_name', many2one_field.comodel_name)
        BaseModel = models.BaseModel
        for Model in self.env.registry.values():
            if not Model._abstract and Model._auto and (
                Model._order_field_to_sql is not BaseModel._order_field_to_sql
                or Model._order_to_sql is not BaseModel._order_to_sql
                or Model._read_group_orderby is not BaseModel._read_group_orderby
            ):
                # methods for customized order are overridden by Model
                # change comodel_name of a many2one field as a hack for the test
                many2one_field.comodel_name = Model._name
                try:
                    Order._read_group([], ['many2one_id'], order='many2one_id')
                except GroupingError as e:
                    self.assertEqual(
                        e, None,
                        f'Bad method override for model {Model._name}. '
                        'Fields used by both customized order and Model._order '
                        'must be added to the query.groupby when query.groupby '
                        'is not empty to avoid GroupingError.'
                    )

    def test_groupby_many2one_with_null_ordering(self):
        orders = self.env['test_read_group.null.order'].create([
            {'name': 'Order 1', 'country_id': self.env.ref('base.us').id},
            {'name': 'Order 2', 'country_id': False},
        ])
        self.env['test_read_group.null.order.line'].create([
            {'null_order_id': orders[0].id},
            {'null_order_id': orders[1].id},
            {'null_order_id': orders[1].id},
            {'null_order_id': orders[0].id},
            {'null_order_id': orders[0].id},
        ])

        result = self.env['test_read_group.null.order.line']._read_group(
            [],
            groupby=['null_order_id'],
            aggregates=['__count'],
            order='null_order_id',
        )
        # as the order is nulls first, the order with no country_id should be first
        self.assertEqual(result, [(orders[1], 2), (orders[0], 3)])
