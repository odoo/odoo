from odoo.exceptions import UserError
from odoo.fields import Command

from odoo.addons.sale.tests.common import SaleCommon


class TestAnalyticToSaleToInvoice(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reinvoice_at_cost_product = cls.env['product.product'].create({
            'name': 'Reinvoice at Cost product',
            'type': 'service',
            'standard_price': 100,
            'list_price': 110,
            'expense_policy': 'cost',
            'invoice_policy': 'delivery',
        })
        cls.reinvoice_at_sales_price_product = cls.env['product.product'].create({
            'name': 'Reinvoice at Sales Price product',
            'type': 'service',
            'standard_price': 100,
            'list_price': 110,
            'expense_policy': 'sales_price',
            'invoice_policy': 'delivery',
        })
        cls.services_sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({
                    'name': 'Reinvoice at Cost Line',
                    'product_id': cls.reinvoice_at_cost_product.id,
                }),
                Command.create({
                    'name': 'Reinvoice at Sales Price Line',
                    'product_id': cls.reinvoice_at_sales_price_product.id,
                }),
            ],
        })

        # confirm the sale order
        cls.services_sale_order.action_confirm()

        cls.at_cost_aal = cls.env['account.analytic.line'].with_context(from_services_and_material=True).create({
            'name': 'At cost Upsale line',
            'product_id': cls.reinvoice_at_cost_product.id,
            'unit_amount': 1,
            'order_id': cls.services_sale_order.id,
        })

        cls.at_sale_price_aal = cls.env['account.analytic.line'].with_context(from_services_and_material=True).create({
            'name': 'At sale price Upsale line',
            'product_id': cls.reinvoice_at_sales_price_product.id,
            'unit_amount': 1,
            'order_id': cls.services_sale_order.id,
        })

    def test_upsale_lines_created_based_on_reinvoice_policy(self):
        """Ensure that services upsold from analytic lines create proper sale order lines
        depending on the product reinvoice policy:

        - For products reinvoiced at cost: a new SO line is always created.
        - For products reinvoiced at sales price: an existing SO line is reused if available.

        Also verify that:
        - Price unit is correctly set based on the reinvoice policy.
        - Analytic account is automatically created on the sale order with the correct plan.
        """
        self.assertEqual(len(self.services_sale_order.order_line), 3)

        reinvoice_at_cost_product_lines = self.services_sale_order.order_line.filtered(
            lambda aal: aal.product_id == self.reinvoice_at_cost_product,
        )
        reinvoice_at_sales_price_product_lines = self.services_sale_order.order_line.filtered(
            lambda aal: aal.product_id == self.reinvoice_at_sales_price_product,
        )

        self.assertEqual(
            len(reinvoice_at_cost_product_lines),
            2,
            "When we upsale a service with reinvoice at cost, we always create a new line",
        )

        at_cost_upsale_order_line = reinvoice_at_cost_product_lines.filtered(
            lambda aal: aal.product_uom_qty == 0,
        )

        self.assertEqual(
            len(at_cost_upsale_order_line),
            1,
            "One line should be created with 0 ordered quantity for at cost product.",
        )

        self.assertEqual(
            len(reinvoice_at_sales_price_product_lines),
            1,
            "When we upsale a service with reinvoice at sales price, we link an existing line if any exists",
        )

        at_sale_price_upsale_order_line = reinvoice_at_sales_price_product_lines

        self.assertEqual(
            at_sale_price_upsale_order_line,
            self.at_sale_price_aal.so_line,
            "Existing line should be linked with the analytic line",
        )
        self.assertEqual(
            at_cost_upsale_order_line,
            self.at_cost_aal.so_line,
            "Newly created line should be linked with the analytic line",
        )

        self.assertEqual(
            at_cost_upsale_order_line.price_unit,
            self.reinvoice_at_cost_product.standard_price,
            "Reinvoice at cost line should have the product cost as price unit",
        )

        self.assertEqual(
            at_sale_price_upsale_order_line.price_unit,
            self.reinvoice_at_sales_price_product.list_price,
            "Reinvoice at sales price line should have the product list price as price unit",
        )

        self.assertIsNotNone(
            self.services_sale_order.analytic_account_id,
            "The sale order should have an analytic account created",
        )

        self.assertEqual(
            self.services_sale_order.analytic_account_id.plan_id,
            self.env.ref('sale.analytic_plan_sale_orders'),
            "The sale order analytic account should have the sale orders analytic plan",
        )

    def test_quantity_update_on_analytic_line_updates_upsale_lines(self):
        """Verify that changing the quantity (unit_amount) on analytic lines correctly
        updates the delivered quantities on the linked sale order lines:

        - Increasing quantity on an at-cost analytic line recomputes delivered qty.
        - Setting quantity to zero on a sales-price analytic line should be recomputed.
        """
        self.at_cost_aal.unit_amount = 3
        self.at_sale_price_aal.unit_amount = 0

        at_cost_upsale_order_line = self.at_cost_aal.so_line
        at_sale_price_upsale_order_line = self.at_sale_price_aal.so_line

        self.assertEqual(
            at_cost_upsale_order_line.qty_delivered,
            3,
            "The delivered quantity should be updated on upsale order line",
        )
        self.assertEqual(
            at_sale_price_upsale_order_line.qty_delivered,
            0,
            "The delivered quantity which was there earlier before creating upsale line should persist",
        )

    def test_changing_sale_order_on_analytic_line_reassigns_upsale_lines(self):
        """Ensure that changing the sale order on analytic lines correctly moves
        the upsale lines to the new sale order:

        - Old upsale lines are removed/updated from the previous order.
        - Delivered quantities are reset or preserved appropriately.
        - New upsale lines are created on the new order with correct values.
        """
        at_cost_upsale_order_line = self.at_cost_aal.so_line
        at_sale_price_upsale_order_line = self.at_sale_price_aal.so_line

        empty_services_sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })

        empty_services_sale_order.action_confirm()

        self.at_cost_aal.with_context(from_services_and_material=True).order_id = empty_services_sale_order
        self.at_sale_price_aal.with_context(from_services_and_material=True).order_id = empty_services_sale_order

        self.assertEqual(
            len(self.services_sale_order.order_line),
            2,
            "Order lines should reset when order changed from services line.",
        )
        self.assertFalse(at_cost_upsale_order_line.exists(), "Lines should be deleted when the sale order is changed from analytic line")
        self.assertEqual(
            at_sale_price_upsale_order_line.qty_delivered,
            0,
            "Delivered quantity increased by analytic line should be reset when the sale order is changed from analytic line",
        )

        new_at_cost_upsale_order_line = empty_services_sale_order.order_line.filtered(
            lambda aal: aal.product_id == self.reinvoice_at_cost_product,
        )

        new_at_sale_price_upsale_order_line = empty_services_sale_order.order_line.filtered(
            lambda aal: aal.product_id == self.reinvoice_at_sales_price_product,
        )

        self.assertEqual(
            len(empty_services_sale_order.order_line),
            2,
            "New lines should be created when the sale order is changed from analytic line",
        )

        self.assertEqual(
            new_at_cost_upsale_order_line.qty_delivered,
            1,
            "Delivered quantity of at cost line should be properly set when the sale order is changed from analytic line",
        )
        self.assertEqual(
            new_at_sale_price_upsale_order_line.qty_delivered,
            1,
            "Delivered quantity of at sale price line should be properly set when the sale order is changed from analytic line",
        )

    def test_changing_product_on_analytic_line_recreates_upsale_lines(self):
        """Verify that updating the product on analytic lines properly updates the
        corresponding sale order lines:

        - Old upsale lines are removed.
        - New lines are created for the new products.
        - Delivered quantities and price units are correctly recomputed.
        """
        at_cost_upsale_order_line = self.at_cost_aal.so_line
        at_sale_price_upsale_order_line = self.at_sale_price_aal.so_line

        reinvoice_at_cost_product_new = self.env['product.product'].create({
            'name': 'New Reinvoice at Cost product',
            'type': 'service',
            'standard_price': 200,
            'list_price': 210,
            'expense_policy': 'cost',
            'invoice_policy': 'delivery',
            'uom_id': self.uom_hour.id,
        })
        reinvoice_at_sales_price_product_new = self.env['product.product'].create({
            'name': 'New Reinvoice at Sales Price product',
            'type': 'service',
            'standard_price': 200,
            'list_price': 210,
            'expense_policy': 'sales_price',
            'invoice_policy': 'delivery',
            'uom_id': self.uom_hour.id,
        })

        self.at_cost_aal.with_context(from_services_and_material=True).product_id = reinvoice_at_cost_product_new
        self.at_sale_price_aal.with_context(from_services_and_material=True).product_id = reinvoice_at_sales_price_product_new

        self.assertFalse(
            at_cost_upsale_order_line.exists(),
            "Old lines should be deleted when the product is changed from analytic line",
        )
        self.assertEqual(
            at_sale_price_upsale_order_line.qty_delivered,
            0,
            "Delivered quantity increased by analytic line should be reset when the product is changed from analytic line",
        )

        new_at_cost_upsale_order_line = self.at_cost_aal.so_line
        new_at_sale_price_upsale_order_line = self.at_sale_price_aal.so_line

        self.assertEqual(
            len(self.services_sale_order.order_line),
            4,
            "New lines should be created when the product is changed from analytic line",
        )

        self.assertEqual(
            new_at_cost_upsale_order_line.qty_delivered,
            1,
            "Delivered quantity of at cost line should be properly set when the product is changed from analytic line",
        )
        self.assertEqual(
            new_at_sale_price_upsale_order_line.qty_delivered,
            1,
            "Delivered quantity of at sale price line should be properly set when the product is changed from analytic line",
        )
        self.assertEqual(
            new_at_cost_upsale_order_line.price_unit,
            reinvoice_at_cost_product_new.standard_price,
            "Price of at cost line should be properly set when the product is changed from analytic line",
        )
        self.assertEqual(
            new_at_sale_price_upsale_order_line.price_unit,
            reinvoice_at_sales_price_product_new.list_price,
            "Price of at sale price line should be properly set when the product is changed from analytic line",
        )

    def test_reinvoicing_creates_invoice_and_locks_analytic_lines(self):
        """Ensure that upsale lines are correctly reinvoiced and that analytic lines
        linked to an invoice become immutable:

        - Invoice is created for upsale lines.
        - Analytic lines are linked to the generated invoice.
        - Analytic lines cannot be modified or deleted once invoiced.
        """
        reinvoice_move_id = self.services_sale_order._create_invoices()
        reinvoice_move_id.action_post()

        self.assertEqual(
            len(reinvoice_move_id.invoice_line_ids),
            2,
            "Upsales lines should be reinvoiced",
        )

        self.assertEqual(
            self.at_cost_aal.reinvoice_move_id,
            reinvoice_move_id,
            "Invoice should be linked to analytic line for at cost line",
        )
        self.assertEqual(
            self.at_sale_price_aal.reinvoice_move_id,
            reinvoice_move_id,
            "Invoice should be linked to analytic line for at sale price line",
        )

        with self.assertRaises(UserError, msg="It shouldn't be possible to delete an analytic line linked to an invoice."):
            self.at_cost_aal.unlink()

        with self.assertRaises(UserError, msg="It shouldn't be possible to delete an analytic line linked to an invoice."):
            self.at_sale_price_aal.unlink()

        with self.assertRaises(UserError, msg="It shouldn't be possible to update an analytic line linked to an invoice."):
            self.at_cost_aal.unit_amount = 9

        with self.assertRaises(UserError, msg="It shouldn't be possible to update an analytic line linked to an invoice."):
            self.at_sale_price_aal.unit_amount = 9

    def test_multiple_analytic_lines_aggregate_on_sales_price_line(self):
        """When multiple analytic lines point to the same sales-price product,
        they should all update the same sale order line instead of creating duplicates.
        """
        extra_at_sale_price_aal = self.env['account.analytic.line'].with_context(from_services_and_material=True).create({
            'name': 'Extra work',
            'product_id': self.reinvoice_at_sales_price_product.id,
            'unit_amount': 2,
            'order_id': self.services_sale_order.id,
        })

        self.assertEqual(
            extra_at_sale_price_aal.so_line,
            self.at_sale_price_aal.so_line,
            "Existing line should be linked to the same sale order line.",
        )

        self.assertEqual(
            self.at_sale_price_aal.so_line.qty_delivered,
            3,
            "Delivered quantity should aggregate from multiple analytic lines."
        )

    def test_analytic_lines_unlink_unsyncs_upsale_lines(self):
        """When analytic lines are deleted, they should unsync the sale order lines.
        For lines with product of
        - At cost expense policy and 0 ordered quantity -> should be deleted.
        - At cost expense policy and non zero ordered quantity -> contributed delivered quantity should be decreased.
        - At cost expense policy and different delivered quantity -> contributed delivered quantity should be decreased.
        - At sale price expense policy -> contributed delivered quantity should be decreased.
        """
        extra_at_sale_price_aal = self.env['account.analytic.line'].with_context(from_services_and_material=True).create({
            'name': 'Extra work At sales Price',
            'product_id': self.reinvoice_at_sales_price_product.id,
            'unit_amount': 2,
            'order_id': self.services_sale_order.id,
        })

        extra_at_cost_aal = self.env['account.analytic.line'].with_context(from_services_and_material=True).create({
            'name': 'Extra work At cost',
            'product_id': self.reinvoice_at_cost_product.id,
            'unit_amount': 2,
            'order_id': self.services_sale_order.id,
        })

        # we need to replicate the case when some nasty user deliberately changes the quantity
        # of the upsale line
        extra_at_cost_aal.so_line.product_uom_qty = 2
        new_at_cost_upsale_order_line = extra_at_cost_aal.so_line
        at_cost_upsale_order_line = self.at_cost_aal.so_line

        extra_at_sale_price_aal.unlink()
        self.at_cost_aal.unlink()
        extra_at_cost_aal.unlink()

        self.assertTrue(
            new_at_cost_upsale_order_line.exists(),
            "Upsale line with non zero ordered quantity should not be deleted for at cost analytic line.",
        )

        self.assertEqual(
            new_at_cost_upsale_order_line.qty_delivered,
            0,
            "Delivered quantity of upsale line with non zero ordered quantity should be decreased for at cost analytic line.",
        )

        self.assertFalse(
            at_cost_upsale_order_line.exists(),
            "Upsale line with 0 ordered quantity should be deleted for at cost analytic line.",
        )

        self.assertEqual(
            self.at_sale_price_aal.so_line.qty_delivered,
            1,
            "Delivered quantity of upsale line should be decreased for at sale price analytic line.",
        )

    def test_negative_quantity_on_analytic_line(self):
        """Negative analytic quantities should not be allowed."""
        with self.assertRaises(UserError, msg="It shouldn't be possible to set negative quantity on analytic line."):
            self.at_cost_aal.with_context(from_services_and_material=True).unit_amount = -1
