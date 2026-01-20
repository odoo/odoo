from odoo.addons.stock.tests.common import TestStockCommon


class TestAnalyticToSaleStock(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_to_upsell = cls.env['product.product'].create({
            'name': 'Upsell Product',
            'type': 'consu',
            'is_storable': True,
            'invoice_policy': 'delivery',
            'expense_policy': 'sales_price',
        })

        cls.env['stock.quant']._update_available_quantity(cls.product_to_upsell, cls.warehouse_1.lot_stock_id, 10)

        cls.stock_and_materials_sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })

        cls.product_to_upsell_sol = cls.env['sale.order.line'].create({
            'name': 'Product to upsell',
            'product_id': cls.product_to_upsell.id,
            'product_uom_qty': 10,
            'order_id': cls.stock_and_materials_sale_order.id,
        })

        cls.stock_and_materials_sale_order.action_confirm()

        cls.stock_and_materials_sale_order.picking_ids.action_assign()
        cls.stock_and_materials_sale_order.picking_ids.button_validate()

        cls.product_to_upsell_aal = cls.env['account.analytic.line'].with_context(from_services_and_material=True).create({
            'name': 'Upsell Product',
            'unit_amount': 5,
            'product_id': cls.product_to_upsell.id,
            'order_id': cls.stock_and_materials_sale_order.id,
        })

    def test_analytic_lines_and_stock_moves_aggregates_delivered_qty(self):
        """Ensure that qty_delivered aggregates quantities from stock moves and upsell analytic lines."""

        self.assertEqual(
            self.product_to_upsell_aal.so_line,
            self.product_to_upsell_sol,
            "The upsell AALs should be linked to the same sale order line.",
        )

        self.assertEqual(
            self.product_to_upsell_sol.qty_delivered,
            15,
            "The delivered quantity should be sum of stock moves and upsell AALs",
        )
