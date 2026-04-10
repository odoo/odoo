# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_stock.tests.common import TestPosStockCommon


class TestPosStockResConfigSettings(TestPosStockCommon):
    """Settings-related tests that need stock models (see pos_stock dependency)."""

    def test_warehouse_synced_with_picking_type(self):
        """Changing the operation type should update the warehouse on the POS config."""
        warehouse_1 = self.env['stock.warehouse'].search(
            self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1
        )
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Second Warehouse',
            'code': 'WH2',
            'company_id': self.env.company.id,
        })

        pos_config = self.env['pos.config'].create({
            'name': 'Shop WH Test',
            'module_pos_restaurant': False,
        })
        self.assertEqual(pos_config.warehouse_id, warehouse_1)
        self.assertEqual(pos_config.picking_type_id.warehouse_id, warehouse_1)

        pos_config.picking_type_id = warehouse_2.pos_type_id
        self.assertEqual(
            pos_config.warehouse_id, warehouse_2,
            "warehouse_id should follow picking_type_id.warehouse_id after changing operation type",
        )
