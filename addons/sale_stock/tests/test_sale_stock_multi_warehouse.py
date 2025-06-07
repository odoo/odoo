# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleStockMultiWarehouse(TestSaleStockCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a.is_storable = True

        cls.warehouse_A = cls.company_data['default_warehouse']
        cls.env['stock.quant']._update_available_quantity(cls.product_a, cls.warehouse_A.lot_stock_id, 10)

        cls.warehouse_B = cls.env['stock.warehouse'].create({
            'name': 'WH B',
            'code': 'WHB',
            'company_id': cls.env.company.id,
            'partner_id': cls.env.company.partner_id.id,
        })
        cls.env['stock.quant']._update_available_quantity(cls.product_a, cls.warehouse_B.lot_stock_id, 10)

        cls.env.user.groups_id |= cls.env.ref('stock.group_stock_user')
        cls.env.user.groups_id |= cls.env.ref('stock.group_stock_multi_locations')
        cls.env.user.groups_id |= cls.env.ref('sales_team.group_sale_salesman')

    def test_multiple_warehouses_generate_multiple_pickings(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'warehouse_id': self.warehouse_A.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 9,
                    'product_uom': self.product_a.uom_id.id,
                    'price_unit': 1,
                    'route_id': self.warehouse_A.delivery_route_id.id,
                }),
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 10,
                    'product_uom': self.product_a.uom_id.id,
                    'price_unit': 1,
                    'route_id': self.warehouse_B.delivery_route_id.id,
                }),
            ],
        })
        so.action_confirm()

        # 2 pickings: 1 per warehouse
        self.assertEqual(len(so.picking_ids), 2)
        # single move per picking
        self.assertEqual(len(so.picking_ids[0].move_ids), 1)
        self.assertEqual(len(so.picking_ids[1].move_ids), 1)
        # pickings comes from the right warehouse
        self.assertEqual(so.picking_ids[0].move_ids[0].location_id.warehouse_id, self.warehouse_A)
        self.assertEqual(so.picking_ids[1].move_ids[0].location_id.warehouse_id, self.warehouse_B)
