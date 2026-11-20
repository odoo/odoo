from odoo import Command
from odoo.tests import tagged
from odoo.addons.repair.tests.test_repair import TestRepairCommon


@tagged('at_install', '-post_install')
class TestRepairReport(TestRepairCommon):

    def test_add_reference_and_remove_reference_for_repair_order(self):
        self.repair1.action_validate()
        picking_receipt = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'partner_id': self.res_partner_1.id,
            'move_ids': [Command.create({
                'product_id': self.product_product_11.id,
                'product_uom_qty': 1,
            })],
        })
        picking_receipt.action_confirm()

        self.env['report.stock.report_reception']._action_assign(
            picking_receipt.move_ids,
            self.repair1.move_ids,
        )
        self.assertEqual(picking_receipt.move_ids.reference_ids, self.repair1.move_ids.reference_ids)

        self.env['report.stock.report_reception']._action_unassign(
            picking_receipt.move_ids,
            self.repair1.move_ids,
        )
        self.assertNotIn(picking_receipt.move_ids.reference_ids, self.repair1.move_ids.reference_ids)
