# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.point_of_sale.tests.test_point_of_sale import TestPointOfSale


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPosStock(TestPointOfSale):

    def test_pos_config_creates_warehouse(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        if warehouse:
            warehouse.write({'active': False, 'name': 'Archived ' + warehouse[0].name})
        pos_config = self.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
        })
        self.assertEqual(pos_config.warehouse_id.code, 'Sho')

    def test_pos_sequence_update_on_warehouse_rename(self):
        """ Test that point of sale sequence prefix is properly updated when warehouse is renamed. """
        main_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        new_warehouse = main_warehouse.copy()

        pos_picking_type = new_warehouse.pos_type_id
        self.assertTrue(pos_picking_type, "POS picking type must be generated for the copied warehouse.")

        new_warehouse.write({'name': 'Test Renamed', 'code': 'TSTRN'})

        expected_prefix = 'TSTRN/POS/'
        self.assertEqual(
            pos_picking_type.sequence_id.prefix,
            expected_prefix,
            "The POS type sequence prefix was not correctly updated."
        )
