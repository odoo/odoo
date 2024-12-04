# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, datetime
from freezegun import freeze_time

from . import common
from odoo import Command
from odoo.tests import Form, tagged


@tagged('-at_install', 'post_install')
class TestWorkcenterOverview(common.TestMrpCommon):

    @freeze_time('2020-03-13')  # Friday
    def test_workcenter_graph_data(self):
        fake_bom = self.env['mrp.bom'].create({
            'product_id': self.product_2.id,
            'product_tmpl_id': self.product_2.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                Command.create({
                    'name': 'Make it look you are working',
                    'workcenter_id': self.workcenter_2.id,
                    'time_cycle_manual': 60, 'sequence': 1})
            ],
            'type': 'normal',
        })

        with self.with_user('admin'):
            lang = self.env['res.lang']._lang_get(self.env.user.lang)
            lang.week_start = '3'   # Wednesday
        week_range, date_start, date_stop = self.workcenter_2._get_week_range_and_first_last_days()
        self.assertEqual(next(iter(week_range)), date_start)
        self.assertEqual(date_stop.strftime('%Y-%m-%d'), '2020-04-07')
        self.assertEqual(list(week_range.items())[2][1], '18 - 24 Mar')

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_2
        mo_form.bom_id = fake_bom
        mo_form.product_qty = 20
        mo_form.save().action_confirm()

        mo_form_2 = Form(self.env['mrp.production'])
        mo_form_2.product_id = self.product_2
        mo_form_2.bom_id = fake_bom
        mo_form_2.product_qty = 60
        mo_form_2.date_start = datetime.today() + timedelta(weeks=1)
        mo_form_2.save().action_confirm()

        wc_load_data = self.workcenter_2._get_workcenter_load_per_week(week_range, date_start, date_stop)
        self.assertListEqual(list(wc_load_data[self.workcenter_2].values()), [20.0, 60.0])
        self.assertListEqual(list(wc_load_data[self.workcenter_2].keys()), [datetime(2020, 3, 11), datetime(2020, 3, 18)])
        load_graph_data = self.workcenter_2._prepare_graph_data(wc_load_data, week_range)
        self.assertEqual(load_graph_data[self.workcenter_2.id][0]['is_sample_data'], False)
        self.assertListEqual(load_graph_data[self.workcenter_2.id][0]['labels'], list(week_range.values()))
        self.assertListEqual(load_graph_data[self.workcenter_2.id][0]['values'], [[0, 20.0, 40.0, 0, 0], 40.0, [0, 0, 20.0, 0, 0]])
