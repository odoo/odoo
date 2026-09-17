from odoo.tests import tagged

from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


@tagged("post_install", "-at_install")
class TestSaleStockMultiWarehouse(
    TestSaleStockCommon, ValuationReconciliationTestCommon
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a.is_storable = True

        cls.warehouse_A = cls.company_data["default_warehouse"]
        cls.env["stock.quant"]._update_available_quantity(
            cls.product_a, cls.warehouse_A.lot_stock_id, 10
        )

        cls.warehouse_B = cls.env["stock.warehouse"].create(
            {
                "name": "WH B",
                "code": "WHB",
                "company_id": cls.env.company.id,
                "partner_id": cls.env.company.partner_id.id,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product_a, cls.warehouse_B.lot_stock_id, 10
        )

        cls.env.user.group_ids |= cls.env.ref("stock.group_stock_user")
        cls.env.user.group_ids |= cls.env.ref("stock.group_stock_multi_locations")
        cls.env.user.group_ids |= cls.env.ref("sale.group_sale_salesman")

    def test_multiple_warehouses_generate_multiple_pickings(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "warehouse_id": self.warehouse_A.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 9,
                            "price_unit": 1,
                            "route_ids": [self.warehouse_A.delivery_route_id.id],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 1,
                            "route_ids": [self.warehouse_B.delivery_route_id.id],
                        },
                    ),
                ],
            }
        )
        so.action_confirm()

        self.assertEqual(len(so.picking_ids), 2)
        # selected by warehouse, not by position: `stock.picking._order` ends
        # `id desc`, and both pickings carry the same date_planned, so indexing
        # asserts which one the procurement happened to create last
        by_warehouse = {
            picking.move_ids.location_id.warehouse_id: picking
            for picking in so.picking_ids
        }
        self.assertEqual(set(by_warehouse), {self.warehouse_A, self.warehouse_B})
        for warehouse in (self.warehouse_A, self.warehouse_B):
            self.assertEqual(len(by_warehouse[warehouse].move_ids), 1)
