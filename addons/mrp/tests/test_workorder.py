# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form


class TestWorkorder(TestMrpCommon):

    def test_workorder_operation_assignment(self):
        """Test that moves aren't automatically assigned to the last workorder
        when the quantity to produce (`product_qty`) is changed.
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_2
        mo = mo_form.save()
        mo.action_confirm()
        wiz = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 5
        })
        wiz.change_prod_qty()
        self.assertFalse(mo.workorder_ids[-1].move_raw_ids)

    def test_workorder_in_progress_expected_duration(self):
        """Test that in progress workorder duration are correctly adapted according to the
        quantity to produce (`product_qty`).
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_4
        mo = mo_form.save()
        mo.action_confirm()
        wo = mo.workorder_ids[0]
        initial_duration = wo.duration_expected
        wo.button_start()
        wiz = self.env['change.production.qty'].create({
            'mo_id': mo.id,
            'product_qty': 2
        })
        wiz.change_prod_qty()
        self.assertEqual(wo.duration_expected, wiz.product_qty * initial_duration)

    @freeze_time('2026-06-11')
    def test_workorder_expected_duration_change(self):
        """Test that the finish date and expected duration are correctly updated
        when the start date or finish date changes.
        """
        self.company.tz = 'Europe/Brussels'
        self.workcenter_2.tz = 'Europe/Brussels'

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo = mo_form.save()
        mo.action_confirm()

        with mo_form.workorder_ids.new() as operation:
            operation.name = "Operation 1"
            operation.workcenter_id = self.workcenter_2
            operation.duration_expected = 60
        mo = mo_form.save()

        workorder = mo.workorder_ids
        start_date = datetime(2026, 6, 11, 12, 0, 0)
        workorder.date_start = start_date
        self.assertEqual(workorder.date_finished, start_date + relativedelta(minutes=60))

        workorder.date_finished = start_date + relativedelta(minutes=90)
        self.assertEqual(workorder.duration_expected, 90)
