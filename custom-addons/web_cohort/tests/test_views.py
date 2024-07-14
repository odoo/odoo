from dateutil.relativedelta import relativedelta

from odoo import Command, fields

from odoo.addons.base.tests.test_views import ViewCase


class TestViews(ViewCase):
    def test_get_views_model_fields(self):
        model = self.env.ref('base.model_ir_ui_view')
        self.env['ir.model.fields'].create([
            {'model_id': model.id, 'name': 'x_date_start', 'ttype': 'datetime'},
            {'model_id': model.id, 'name': 'x_date_stop', 'ttype': 'datetime'},
        ])

        view = self.assertValid(
            """
                <cohort string="foo" date_start="x_date_start" date_stop="x_date_stop" interval="week" mode="churn" sample="1">
                    <field name="priority"/>
                </cohort>
            """
        )

        views = self.View.get_views([(view.id, 'cohort')])
        self.assertTrue('x_date_start' in views['models']['ir.ui.view'])
        self.assertTrue('x_date_start' in views['models']['ir.ui.view'])

    def test_cohort_data(self):
        # create a model with 2 dates field
        self.env['ir.model'].create({
            'name': 'Stuff',
            'model': 'x_stuff',
            'field_id': [
                Command.create(
                    {'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
                Command.create(
                    {'name': 'x_date_start', 'ttype': 'date', 'field_description': 'Start Date'}),
                Command.create(
                    {'name': 'x_date_stop', 'ttype': 'date', 'field_description': 'End Date'}),
            ]
        })
        # create 2 stuffs: one from 6 months ago without an end date,
        # and one from 4 months ago with an end date 1 month ago
        self.env['x_stuff'].create([
            {
                'x_name': 'Stuff 1',
                'x_date_start': fields.Date.today() - relativedelta(months=6),
            }, {
                'x_name': 'Stuff 2',
                'x_date_start': fields.Date.today() - relativedelta(months=4),
                'x_date_stop': fields.Date.today() - relativedelta(months=1),
            }
        ])

        # check that the cohort method returns the correct data
        cohort = self.env['x_stuff'].get_cohort_data(
            'x_date_start', 'x_date_stop', '__count', 'month', [], 'retention', 'forward')

        # first row should be 6 mmonths ago, with 1 stuff counted until *now*
        first_row = cohort['rows'][0]
        value_per_month = list(
            map(lambda col: col['value'], first_row['columns']))
        # we should have 7 periods with value 1 (6 prev periods + current period),
        # then the rest with no value (9 periods) (16 periods in total)
        self.assertEqual(value_per_month, [1]*7 + ['-']*9)
        expected_period_domain = [
            '&',
            ('x_date_start', '!=', False),
            '&',
            ('x_date_start', '>=', (fields.Date.today() -
             relativedelta(months=6)).replace(day=1)),
            ('x_date_start', '<', (fields.Date.today() -
             relativedelta(months=5)).replace(day=1)),
        ]
        self.assertEqual(first_row['domain'], expected_period_domain)
        # check for the second row
        second_row = cohort['rows'][1]
        value_per_month = list(
            map(lambda col: col['value'], second_row['columns']))
        # we should have 3 periods with value 1, then 2 with value 0 (closing period + current period),
        # then the rest with no value (11 periods) (16 periods in total)
        self.assertEqual(value_per_month, [1.0]*3 + [0]*2 + ['-']*11)
        expected_period_domain = [
            '&',
            ('x_date_start', '!=', False),
            '&',
            ('x_date_start', '>=', (fields.Date.today() -
             relativedelta(months=4)).replace(day=1)),
            ('x_date_start', '<', (fields.Date.today() -
             relativedelta(months=3)).replace(day=1)),
        ]
        self.assertEqual(second_row['domain'], expected_period_domain)
