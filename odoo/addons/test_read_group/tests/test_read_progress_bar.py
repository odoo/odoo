# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
from odoo.tools import mute_logger


@common.tagged('post_install', '-at_install')
class TestReadProgressBar(common.TransactionCase):
    """Test for read_progress_bar"""

    def setUp(self):
        super(TestReadProgressBar, self).setUp()
        self.Model = self.env['res.partner']

    def test_read_progress_bar_m2m(self):
        """ Test that read_progress_bar works with m2m field grouping """
        progressbar = {
            'field': 'type',
            'colors': {
                'contact': 'success', 'private': 'danger', 'other': '200',
            }
        }
        result = self.env['res.partner'].read_progress_bar([], 'category_id', progressbar)
        # check that it works when grouping by m2m field
        self.assertTrue(result)
        # check the null group
        self.assertIn('False', result)

    def test_week_grouping(self):
        """The labels associated to each record in read_progress_bar should match
        the ones from formatted_read_group, even in edge cases like en_US locale on sundays
        """
        context = {"lang": "en_US"}
        groupby = "date:week"
        self.Model.create({'date': '2021-05-02', 'name': "testWeekGrouping_first"})  # Sunday
        self.Model.create({'date': '2021-05-09', 'name': "testWeekGrouping_second"})  # Sunday
        progress_bar = {
            'field': 'name',
            'colors': {
                "testWeekGrouping_first": 'success',
                "testWeekGrouping_second": 'danger',
            }
        }

        groups = self.Model.with_context(context).formatted_read_group(
            [('name', "like", "testWeekGrouping%")], groupby=[groupby])
        progressbars = self.Model.with_context(context).read_progress_bar(
            [('name', "like", "testWeekGrouping%")], group_by=groupby, progress_bar=progress_bar)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(progressbars), 2)

        # format the read_progress_bar result to get a dictionary under this format : {record_name: group_name}
        # original format (after read_progress_bar) is : {group_name: {record_name: count}}
        pg_groups = {
            next(record_name for record_name, count in data.items() if count): group_name
            for group_name, data in progressbars.items()
        }
        self.assertEqual(groups[0][groupby][0], pg_groups["testWeekGrouping_first"])
        self.assertEqual(groups[1][groupby][0], pg_groups["testWeekGrouping_second"])

    def test_simple(self):
        model = self.env['ir.model'].create({
            'model': 'x_progressbar',
            'name': 'progress_bar',
            'field_id': [
                (0, 0, {
                    'field_description': 'Country',
                    'name': 'x_country_id',
                    'ttype': 'many2one',
                    'relation': 'res.country',
                }),
                (0, 0, {
                    'field_description': 'Date',
                    'name': 'x_date',
                    'ttype': 'date',
                }),
                (0, 0, {
                    'field_description': 'State',
                    'name': 'x_state',
                    'ttype': 'selection',
                    'selection': "[('foo', 'Foo'), ('bar', 'Bar'), ('baz', 'Baz')]",
                }),
            ],
        })

        c1, c2, c3 = self.env['res.country'].search([], limit=3)

        self.env['x_progressbar'].create([
            # week 1 2019
            {'x_country_id': c1.id, 'x_date': '2019-01-01', 'x_state': 'foo'},
            {'x_country_id': c1.id, 'x_date': '2019-01-02', 'x_state': 'foo'},
            {'x_country_id': c1.id, 'x_date': '2019-01-03', 'x_state': 'foo'},
            {'x_country_id': c1.id, 'x_date': '2019-01-04', 'x_state': 'bar'},
            {'x_country_id': c1.id, 'x_date': '2019-01-05', 'x_state': 'baz'},
            # week 2 2019
            {'x_country_id': c2.id, 'x_date': '2019-01-06', 'x_state': 'foo'},
            {'x_country_id': c2.id, 'x_date': '2019-01-07', 'x_state': 'bar'},
            {'x_country_id': c2.id, 'x_date': '2019-01-08', 'x_state': 'bar'},
            {'x_country_id': c2.id, 'x_date': '2019-01-09', 'x_state': 'baz'},
            {'x_country_id': c3.id, 'x_date': '2019-01-10', 'x_state': 'baz'},
            {'x_country_id': c3.id, 'x_date': '2019-01-11', 'x_state': 'foo'},
            {'x_country_id': c3.id, 'x_date': '2019-01-12', 'x_state': 'foo'},
            # week 3 2019
            {'x_country_id': c3.id, 'x_date': '2019-01-13', 'x_state': 'baz'},
            {'x_country_id': c3.id, 'x_date': '2019-01-14', 'x_state': 'baz'},
            {'x_country_id': c3.id, 'x_date': '2019-01-15', 'x_state': 'baz'},
        ])

        progress_bar = {
            'field': 'x_state',
            'colors': {'foo': 'success', 'bar': 'warning', 'baz': 'danger'},
        }
        result = self.env['x_progressbar'].read_progress_bar([], 'x_country_id', progress_bar)
        self.assertEqual(result, {
            str(c1.id): {'foo': 3, 'bar': 1, 'baz': 1},
            str(c2.id): {'foo': 1, 'bar': 2, 'baz': 1},
            str(c3.id): {'foo': 2, 'bar': 0, 'baz': 4},
        })

        # check date aggregation and format
        result = self.env['x_progressbar'].read_progress_bar([], 'x_date:week', progress_bar)
        self.assertEqual(result, {
            '2018-12-30': {'foo': 3, 'bar': 1, 'baz': 1},
            '2019-01-06': {'foo': 3, 'bar': 2, 'baz': 2},
            '2019-01-13': {'foo': 0, 'bar': 0, 'baz': 3},
        })

        # add a computed field on model
        model.write({'field_id': [
            (0, 0, {
                'field_description': 'Related State',
                'name': 'x_state_computed',
                'ttype': 'selection',
                'selection': "[('foo', 'Foo'), ('bar', 'Bar'), ('baz', 'Baz')]",
                'compute': "for rec in self: rec['x_state_computed'] = rec.x_state",
                'depends': 'x_state',
                'readonly': True,
                'store': False,
            }),
        ]})

        progress_bar = {
            'field': 'x_state_computed',
            'colors': {'foo': 'success', 'bar': 'warning', 'baz': 'danger'},
        }
        # It is not possible to read_progress_bar with ungroupable fields
        with self.assertRaises(ValueError), mute_logger('odoo.domains'):
            self.env['x_progressbar'].read_progress_bar([], 'x_country_id', progress_bar)
