from odoo.tests import common


class TestWebReadGroup(common.TransactionCase):
    """ Test the 'length' logic of web_read_group, groups logic
    are tested in test_formatted_read_group """

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # For Monetary Aggregates
        cls.usd = cls.env.ref('base.USD')
        cls.usd.active = True
        cls.eur = cls.env.ref('base.EUR')
        cls.eur.active = True

        cls.MonetaryAggRelated = cls.env['test_read_group.aggregate.monetary.related']
        cls.MonetaryAgg = cls.env['test_read_group.aggregate.monetary']

        cls.related_model_usd = cls.MonetaryAggRelated.create({'stored_currency_id': cls.usd.id})
        cls.related_model_eur = cls.MonetaryAggRelated.create({'stored_currency_id': cls.eur.id})


    def test_limit_offset_performance(self):
        Model = self.env['test_read_group.aggregate']
        Model.create({'key': 1, 'value': 1})
        Model.create({'key': 1, 'value': 2})
        Model.create({'key': 1, 'value': 3})
        Model.create({'key': 2, 'value': 4})
        Model.create({'key': 2})
        Model.create({'key': 2, 'value': 5})
        Model.create({})
        Model.create({'value': 6})

        # warmup
        Model.web_read_group([], groupby=['key'], aggregates=['value:sum'])

        # One _read_group/query because limit is reached
        with self.assertQueryCount(1):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], limit=4),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                        {'__extra_domain': [('key', '=', False)], 'key': False, 'value:sum': 6},
                    ],
                    'length': 3,
                },
            )

        # One _read_group with the limit and other without to get the length
        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], limit=2),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                    ],
                    'length': 3,
                },
            )

        # One _read_group/query because limit is reached
        with self.assertQueryCount(1):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], offset=1),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                        {'__extra_domain': [('key', '=', False)], 'key': False, 'value:sum': 6},
                    ],
                    'length': 3,
                },
            )

        with self.assertQueryCount(2):
            self.assertEqual(
                Model.web_read_group([], groupby=['key'], aggregates=['value:sum'], offset=1, limit=2, order='key DESC'),
                {
                    'groups': [
                        {'__extra_domain': [('key', '=', 2)], 'key': 2, 'value:sum': 4 + 5},
                        {'__extra_domain': [('key', '=', 1)], 'key': 1, 'value:sum': 1 + 2 + 3},
                    ],
                    'length': 3,
                },
            )

    def test_web_read_group_different_currencies(self):
        records_name = 'Some name'
        record1 = self.MonetaryAgg.create({
            'name': records_name,
            'related_model_id': self.related_model_usd.id,
            'currency_id': self.usd.id,
            'total_in_currency_id': 10.0,
            'total_in_related_stored_currency_id': 10.0,
        })
        record2 = self.MonetaryAgg.create({
            'name': records_name,
            'related_model_id': self.related_model_eur.id,
            'currency_id': self.eur.id,
            'total_in_currency_id': 15.0,
            'total_in_related_stored_currency_id': 15.0,
        })
        read_group_res = self.MonetaryAgg.web_read_group(
            [], groupby=['name'],
            aggregates=['total_in_currency_id:sum', 'total_in_related_stored_currency_id:sum'],
        )

        self.assertEqual(read_group_res['length'], 1)
        group = read_group_res['groups'][0]

        self.assertFalse(group['total_in_currency_id:sum'])
        self.assertFalse(group['total_in_related_stored_currency_id:sum'])

    def test_web_read_group_same_currencies(self):
        records_name = 'Some name'
        record1 = self.MonetaryAgg.create({
            'name': records_name,
            'related_model_id': self.related_model_usd.id,
            'currency_id': self.usd.id,
            'total_in_currency_id': 10.0,
            'total_in_related_stored_currency_id': 10.0,
        })
        record2 = self.MonetaryAgg.create({
            'name': records_name,
            'related_model_id': self.related_model_usd.id,
            'currency_id': self.usd.id,
            'total_in_currency_id': 15.0,
            'total_in_related_stored_currency_id': 15.0,
        })
        read_group_res = self.MonetaryAgg.web_read_group(
            [], groupby=['name'],
            aggregates=['total_in_currency_id:sum', 'total_in_related_stored_currency_id:sum'],
        )

        self.assertEqual(read_group_res['length'], 1)
        group = read_group_res['groups'][0]

        self.assertAlmostEqual(group['total_in_currency_id:sum'], 25.0)
        self.assertAlmostEqual(group['total_in_related_stored_currency_id:sum'], 25.0)

    def test_web_read_group_mixed_currencies(self):
        records_name = 'Some name'
        record1 = self.MonetaryAgg.create({
            'name': records_name,
            'related_model_id': self.related_model_usd.id,
            'currency_id': self.usd.id,
            'total_in_currency_id': 10.0,
            'total_in_related_stored_currency_id': 10.0,
        })
        record2 = self.MonetaryAgg.create({
            'name': records_name,
            'related_model_id': self.related_model_usd.id,
            'currency_id': self.eur.id,
            'total_in_currency_id': 15.0,
            'total_in_related_stored_currency_id': 15.0,
        })
        read_group_res = self.MonetaryAgg.web_read_group(
            [], groupby=['name'],
            aggregates=['total_in_currency_id:sum', 'total_in_related_stored_currency_id:sum'],
        )

        self.assertEqual(read_group_res['length'], 1)
        group = read_group_res['groups'][0]

        self.assertFalse(group['total_in_currency_id:sum'])
        self.assertAlmostEqual(group['total_in_related_stored_currency_id:sum'], 25.0)

    def test_web_read_group_none_currencies(self):
        records_name = 'Some name'
        record1 = self.MonetaryAgg.create({
            'name': records_name,
            'currency_id': False,
            'total_in_currency_id': 10.0,
        })
        record2 = self.MonetaryAgg.create({
            'name': records_name,
            'currency_id': False,
            'total_in_currency_id': 15.0,
        })
        read_group_res = self.MonetaryAgg.web_read_group(
            [], groupby=['name'],
            aggregates=['total_in_currency_id:sum'],
        )

        self.assertEqual(read_group_res['length'], 1)
        group = read_group_res['groups'][0]

        self.assertFalse(group['total_in_currency_id:sum'])

    def test_web_read_group_mixed_one_and_none_currencies(self):
        records_name = 'Some name'
        record1 = self.MonetaryAgg.create({
            'name': records_name,
            'currency_id': self.usd.id,
            'total_in_currency_id': 10.0,
        })
        record2 = self.MonetaryAgg.create({
            'name': records_name,
            'currency_id': False,
            'total_in_currency_id': 15.0,
        })
        read_group_res = self.MonetaryAgg.web_read_group(
            [], groupby=['name'],
            aggregates=['total_in_currency_id:sum'],
        )

        self.assertEqual(read_group_res['length'], 1)
        group = read_group_res['groups'][0]

        self.assertFalse(group['total_in_currency_id:sum'])

    def test_web_read_group_non_stored_currency(self):
        self.MonetaryAgg.create({
            'name': "Some name",
            'related_model_id': self.related_model_usd.id,
            'total_in_related_non_stored_currency_id': 10.0,
        })
        with self.assertRaises(ValueError):
            read_group_res = self.MonetaryAgg.web_read_group(
                [], groupby=['name'],
                aggregates=['total_in_related_non_stored_currency_id:sum'],
            )

    def test_monetary_fields_agg_in_fields_get(self):
        field_infos = self.MonetaryAgg.fields_get()

        self.assertEqual(field_infos['total_in_currency_id'].get('aggregator'), 'sum')
        self.assertEqual(field_infos['total_in_related_stored_currency_id'].get('aggregator'), 'sum')
        self.assertFalse(field_infos['total_in_related_non_stored_currency_id'].get('aggregator'), False)
