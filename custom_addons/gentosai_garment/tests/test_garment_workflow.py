# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestGarmentWorkflow(TestMrpCommon):

    def test_new_manufacturing_order_starts_pending(self):
        mo, *_ = self.generate_mo()

        self.assertEqual(mo.garment_stage, 'pending')

    def test_garment_stage_advances_in_order(self):
        mo, *_ = self.generate_mo()

        for expected in ('cutting', 'sewing', 'finishing', 'packing', 'done'):
            mo.action_advance_garment_stage()
            self.assertEqual(mo.garment_stage, expected)

    def test_completed_garment_workflow_cannot_advance(self):
        mo, *_ = self.generate_mo()
        mo.garment_stage = 'done'

        with self.assertRaises(UserError):
            mo.action_advance_garment_stage()

    def test_draft_manufacturing_order_cannot_advance(self):
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_4
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        self.assertEqual(mo.state, 'draft')

        with self.assertRaises(UserError):
            mo.action_advance_garment_stage()

    def test_cancelled_manufacturing_order_cannot_advance(self):
        mo, *_ = self.generate_mo()
        mo.action_cancel()

        with self.assertRaises(UserError):
            mo.action_advance_garment_stage()
