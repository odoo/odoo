# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form
from odoo.addons.quality_control.tests.test_common import TestQualityCommon
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestMrpSubcontractingQuality(TestQualityCommon, TestMrpSubcontractingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.passfail_control_point = cls.env['quality.point'].create({
            'title': 'subcontracting control point',
            'product_ids': [Command.link(cls.finished.id)],
            'picking_type_ids': [Command.link(cls.warehouse.in_type_id.id)],
            'test_type_id': cls.env.ref('quality_control.test_type_passfail').id,
            'measure_on': 'move_line',
            'failure_location_ids': [Command.link(cls.failure_location.id)],
        })

    def _record_qty(self, receipt, recorded_qty, finished_lot_id=None, comp_lot_ids=None):
        action = receipt.action_record_components()
        mo_form = Form.from_action(self.env, action)
        mo_form.qty_producing = recorded_qty
        if finished_lot_id:
            mo_form.lot_producing_id = finished_lot_id
            if comp_lot_ids:
                for i, lot_id in enumerate(comp_lot_ids):
                    with mo_form.move_line_raw_ids.edit(i) as ml:
                        ml.lot_id = lot_id
        mo_form.save().subcontracting_record_component()

    def _quality_fail(self, checks, failed_qty):
        action = checks.action_open_quality_check_wizard()
        quality_check = Form.from_action(self.env, action).save()
        next_action = quality_check.do_fail()
        next_quality_check = Form.from_action(self.env, next_action)
        next_quality_check.qty_failed = failed_qty
        next_quality_check.save().confirm_fail()

    def test_subcontracting_partial_quality_failure_consumes_components_lot(self):
        """
        Check that quality failures are applied to the correct subcontracted productions
        when components are recorded multiple times with different finished product lots.

        Two component recordings are done on the same receipt, each linked to a different
        finished lot. When a quality check partially fails for each lot, only the raw
        material moves belonging to the corresponding production should be reduced.
        """
        (self.finished | self.comp1 | self.comp2).tracking = 'lot'
        finished_lot_id, comp_1_lot_id, comp_2_lot_id,\
        finished_lot_id_2, comp_1_lot_id_2, comp_2_lot_id_2 = self.env['stock.lot'].create(
            [
                {'name': name, 'product_id': product_id}
                for i in range(2)
                for name, product_id in (
                    (f'finished_lot_{i}', self.finished.id),
                    (f'comp1_lot_{i}', self.comp1.id),
                    (f'comp2_lot_{i}', self.comp2.id),
                )
            ]
        )

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_in'),
            'partner_id': self.subcontractor_partner1.id,
            'move_ids_without_package': [Command.create({
                'name': self.finished.display_name,
                'product_id': self.finished.id,
                'product_uom_qty': 16,
                'product_uom': self.finished.uom_id.id,
            })],
        })
        receipt.action_confirm()
        # Record quantity for two different lots
        self._record_qty(receipt, 10, finished_lot_id, comp_lot_ids=comp_1_lot_id | comp_2_lot_id)
        self._record_qty(receipt, 3, finished_lot_id_2, comp_lot_ids=comp_1_lot_id_2 | comp_2_lot_id_2)
        # Quality check for two different lots
        self._quality_fail(receipt.check_ids.filtered(lambda c: c.lot_line_id == finished_lot_id), 6)
        self._quality_fail(receipt.check_ids.filtered(lambda c: c.lot_line_id == finished_lot_id_2), 1)
        self.assertRecordValues(
            receipt.move_ids.move_orig_ids.production_id.move_raw_ids.sorted('id'),
            [
                {'quantity': 4, 'order_finished_lot_id': finished_lot_id.id},
                {'quantity': 4, 'order_finished_lot_id': finished_lot_id.id},
                {'quantity': 2, 'order_finished_lot_id': finished_lot_id_2.id},
                {'quantity': 2, 'order_finished_lot_id': finished_lot_id_2.id},
                {'quantity': 3, 'order_finished_lot_id': False},
                {'quantity': 3, 'order_finished_lot_id': False},
            ]
        )
        # Check we can still reserve quantity
        self.assertTrue(receipt.check_ids.action_open_quality_check_wizard() is not True)

    def test_subcontracting_partial_quality_failure_consumes_components(self):
        """
        Ensure that a partial quality failure on a subcontracted receipt correctly
        reduces the quantities of the recorded production.

        After recording a production, a quality check that partially fails should
        only reduce the corresponding raw material moves, leaving the remaining
        quantities untouched.
        """
        self.bom.consumption = 'warning'
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.ref('stock.picking_type_in'),
            'partner_id': self.subcontractor_partner1.id,
            'move_ids_without_package': [Command.create({
                'name': self.finished.display_name,
                'product_id': self.finished.id,
                'product_uom_qty': 12,
                'product_uom': self.finished.uom_id.id,
            })],
        })
        receipt.action_confirm()
        self._record_qty(receipt, 8)
        self._quality_fail(receipt.check_ids, 6)
        self.assertRecordValues(
            receipt.move_ids.move_orig_ids.production_id.move_raw_ids.sorted('id'),
            [{'quantity': 2}, {'quantity': 2}, {'quantity': 4}, {'quantity': 4}]
        )
        # Check we can still reserve quantity
        self.assertTrue(receipt.check_ids.action_open_quality_check_wizard() is not True)
