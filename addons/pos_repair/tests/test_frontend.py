# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):

    def test_pos_repair(self):
        self.product_1 = self.env['product.product'].create({
            'name': 'Test product 1'
        })
        self.stock_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.repair1 = self.env['repair.order'].create({
            'product_id': self.product_1.id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                    'company_id': self.env.company.id,
                })
            ],
            'partner_id': self.env['res.partner'].create({'name': 'Partner 1'}).id
        })
        self.repair1._action_repair_confirm()
        self.repair1.action_repair_start()
        self.repair1.action_repair_end()
        self.repair1.sudo().action_create_sale_order()
        self.assertEqual(len(self.product_1.stock_move_ids.ids), 2, "There should be 2 stock moves for the product created by the repair order")
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosRepairSettleOrder', login="pos_user")
        self.assertEqual(len(self.product_1.stock_move_ids.ids), 2, "Paying for the order in PoS should not create new stock moves")
