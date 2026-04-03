# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from odoo import fields
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

    def test_workorder_gantt_reschedule(self):
        mo = self.env['mrp.production'].create({
            'bom_id': self.bom_3.id,
        })
        mo.action_confirm()
        mo.button_plan()

        #  related work-orders
        wos = mo.workorder_ids
        self.assertEqual(len(wos), 3)

        # Reset middle WO dates
        wo_from = Form(wos[1])
        wo_from.date_start = False
        wo_from.date_finished = False
        wo_from.save()

        # Compute new dates for first WO
        base_dt = fields.Datetime.now() + timedelta(days=7)
        end_dt = base_dt + timedelta(hours=wos[0].duration_expected)
        vals = {
            'date_start':  fields.Datetime.to_string(base_dt),
            'date_finished': fields.Datetime.to_string(end_dt)
        }
        reschedule = self.env['mrp.workorder'].web_gantt_reschedule(
            vals,
            'maintainBuffer',
            wos[0].id,
            'blocked_by_workorder_ids',
            'needed_by_workorder_ids',
            'date_start',
            'date_finished',
        )
        self.assertEqual(reschedule.get('type'), "success")
        self.assertEqual(
            fields.Datetime.to_string(wos[0].date_start),
            fields.Datetime.to_string(base_dt),
        )
