
# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase


class TestReadGroupInherits(TransactionCase):

    def test_read_group_inherits(self):
        country1 = self.env['res.country'].create({'name': 'country Sir', 'code': 'WW'})
        country2 = self.env['res.country'].create({'name': 'country Lady', 'code': 'ZZ'})
        user_vals_list = [
            {'name': 'Alice', 'login': 'alice', 'color': 1, 'function': 'Friend', 'date': '2015-03-28', 'country_id': country2.id},
            {'name': 'Alice', 'login': 'alice2', 'color': 0, 'function': 'Friend', 'date': '2015-01-28', 'country_id': country2.id},
            {'name': 'Bob', 'login': 'bob', 'color': 2, 'function': 'Friend', 'date': '2015-03-02', 'country_id': country1.id},
            {'name': 'Eve', 'login': 'eve', 'color': 3, 'function': 'Eavesdropper', 'date': '2015-03-20', 'country_id': country2.id},
            {'name': 'Nab', 'login': 'nab', 'color': -3, 'function': '5$ Wrench', 'date': '2014-09-10', 'country_id': country1.id},
            {'name': 'Nab', 'login': 'nab-she', 'color': 6, 'function': '5$ Wrench', 'date': '2014-01-02', 'country_id': country2.id},
        ]
        res_users = self.env['res.users']
        users = res_users.create(user_vals_list)
        domain = [('id', 'in', users.ids)]

        # group on local char field without domain and without active_test (-> empty WHERE clause)
        groups_data = res_users.with_context(active_test=False).read_group([], fields=['login'], groupby=['login'], orderby='login DESC')
        self.assertGreater(len(groups_data), 6, "Incorrect number of results when grouping on a field")

        # group on local char field with limit
        groups_data = res_users.read_group(domain, fields=['login'], groupby=['login'], orderby='login DESC', limit=3, offset=3)
        self.assertEqual(len(groups_data), 3, "Incorrect number of results when grouping on a field with limit")
        self.assertEqual([g['login'] for g in groups_data], ['bob', 'alice2', 'alice'], 'Result mismatch')

        # group on inherited char field, aggregate on int field (second groupby ignored on purpose)
        groups_data = res_users.read_group(domain, fields=['name', 'color', 'function'], groupby=['function', 'login'])
        self.assertEqual(len(groups_data), 3, "Incorrect number of results when grouping on a field")
        self.assertEqual(['5$ Wrench', 'Eavesdropper', 'Friend'], [g['function'] for g in groups_data], 'incorrect read_group order')
        for group_data in groups_data:
            self.assertIn('color', group_data, "Aggregated data for the column 'color' is not present in read_group return values")
            self.assertEqual(group_data['color'], 3, "Incorrect sum for aggregated data for the column 'color'")

        # group on inherited char field, reverse order
        groups_data = res_users.read_group(domain, fields=['name', 'color'], groupby='name', orderby='name DESC')
        self.assertEqual([g['name'] for g in groups_data], ['Nab', 'Eve', 'Bob', 'Alice'], 'Incorrect ordering of the list')

        # group on int field, default ordering
        groups_data = res_users.read_group(domain, fields=['color'], groupby='color')
        self.assertEqual([g['color'] for g in groups_data], [-3, 0, 1, 2, 3, 6], 'Incorrect ordering of the list')

        # multi group, second level is int field, should still be summed in first level grouping
        groups_data = res_users.read_group(domain, fields=['name', 'color'], groupby=['name', 'color'], orderby='name DESC')
        self.assertEqual([g['name'] for g in groups_data], ['Nab', 'Eve', 'Bob', 'Alice'], 'Incorrect ordering of the list')
        self.assertEqual([g['color'] for g in groups_data], [3, 3, 2, 1], 'Incorrect ordering of the list')

        # group on inherited char field, multiple orders with directions
        groups_data = res_users.read_group(domain, fields=['name', 'color'], groupby='name', orderby='color DESC, name')
        self.assertEqual(len(groups_data), 4, "Incorrect number of results when grouping on a field")
        self.assertEqual([g['name'] for g in groups_data], ['Eve', 'Nab', 'Bob', 'Alice'], 'Incorrect ordering of the list')
        self.assertEqual([g['name_count'] for g in groups_data], [1, 2, 1, 2], 'Incorrect number of results')

        # group on inherited date column (res_partner.date) -> Year-Month, default ordering
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'date'], groupby=['date'])
        self.assertEqual(len(groups_data), 4, "Incorrect number of results when grouping on a field")
        self.assertEqual([g['date'] for g in groups_data], ['January 2014', 'September 2014', 'January 2015', 'March 2015'], 'Incorrect ordering of the list')
        self.assertEqual([g['date_count'] for g in groups_data], [1, 1, 1, 3], 'Incorrect number of results')

        # group on inherited date column (res_partner.date) specifying the :year -> Year default ordering
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'date'], groupby=['date:year'])
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        self.assertEqual([g['date:year'] for g in groups_data], ['2014', '2015'], 'Incorrect ordering of the list')
        self.assertEqual([g['date_count'] for g in groups_data], [2, 4], 'Incorrect number of results')

        # group on inherited date column (res_partner.date) -> Year-Month, custom order
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'date'], groupby=['date'], orderby='date DESC')
        self.assertEqual(len(groups_data), 4, "Incorrect number of results when grouping on a field")
        self.assertEqual([g['date'] for g in groups_data], ['March 2015', 'January 2015', 'September 2014', 'January 2014'], 'Incorrect ordering of the list')
        self.assertEqual([g['date_count'] for g in groups_data], [3, 1, 1, 1], 'Incorrect number of results')

        # group on inherited many2one (res_partner.country_id), default order
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'country_id'], groupby=['country_id'])
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([g['country_id'] for g in groups_data], [(country2.id, 'country Lady'), (country1.id, 'country Sir')], 'Incorrect ordering of the list')
        self.assertEqual([g['country_id_count'] for g in groups_data], [4, 2], 'Incorrect number of results')
        self.assertEqual([g['color'] for g in groups_data], [10, -1], 'Incorrect aggregation of int column')

        # group on inherited many2one (res_partner.country_id), reversed natural order
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'country_id'], groupby=['country_id'], orderby="country_id desc")
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([(country1.id, 'country Sir'), (country2.id, 'country Lady')], [g['country_id'] for g in groups_data], 'Incorrect ordering of the list')
        self.assertEqual([g['country_id_count'] for g in groups_data], [2, 4], 'Incorrect number of results')
        self.assertEqual([g['color'] for g in groups_data], [-1, 10], 'Incorrect aggregation of int column')

        # group on inherited many2one (res_partner.country_id), multiple orders with m2o in second position
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'country_id'], groupby=['country_id'], orderby="color desc, country_id desc")
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([g['country_id'] for g in groups_data], [(country2.id, 'country Lady'), (country1.id, 'country Sir')], 'Incorrect ordering of the result')
        self.assertEqual([g['country_id_count'] for g in groups_data], [4, 2], 'Incorrect number of results')
        self.assertEqual([g['color'] for g in groups_data], [10, -1], 'Incorrect aggregation of int column')

        # group on inherited many2one (res_partner.country_id), ordered by other inherited field (color)
        groups_data = res_users.read_group(domain, fields=['function', 'color', 'country_id'], groupby=['country_id'], orderby='color')
        self.assertEqual(len(groups_data), 2, "Incorrect number of results when grouping on a field")
        # m2o is returned as a (id, label) pair
        self.assertEqual([g['country_id'] for g in groups_data], [(country1.id, 'country Sir'), (country2.id, 'country Lady')], 'Incorrect ordering of the list')
        self.assertEqual([g['country_id_count'] for g in groups_data], [2, 4], 'Incorrect number of results')
        self.assertEqual([g['color'] for g in groups_data], [-1, 10], 'Incorrect aggregation of int column')
