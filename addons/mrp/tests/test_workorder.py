# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

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

    def test_workorder_date_start_preserves_duration(self):
        """Changing only date_start should shift date_finished, not shrink duration."""
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_2
        mo = mo_form.save()
        mo.action_confirm()
        wo = mo.workorder_ids[0]
        date_start = datetime(2025, 6, 2, 8, 0, 0)
        date_finished = datetime(2025, 6, 2, 11, 0, 0)
        wo.with_context(bypass_duration_calculation=True).write({
            'date_start': date_start,
            'date_finished': date_finished,
        })
        original_duration = wo.duration_expected
        new_start = datetime(2025, 6, 2, 10, 0, 0)
        wo.write({'date_start': new_start})
        self.assertAlmostEqual(wo.duration_expected, original_duration, places=1)
        self.assertGreater(wo.date_finished, date_finished)
