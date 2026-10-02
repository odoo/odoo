from os.path import dirname, join

from vcr import VCR

from .test_woo_backend import BaseWooTestCase

recorder = VCR(
    cassette_library_dir=join(dirname(__file__), "fixtures/cassettes"),
    decode_compressed_response=True,
    filter_headers=["Authorization"],
    path_transformer=VCR.ensure_suffix(".yaml"),
    record_mode="once",
)


class TestImportSaleOrder(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Sale order."""
        super().setUp()

    def test_import_sale_order(self):
        """Test Assertions for Sale order"""
        external_id = "71"

        with recorder.use_cassette("import_woo_product_and_order"):
            self.env["woo.sale.order"].import_record(
                external_id=external_id, backend=self.backend
            )
        sale_order1 = self.env["woo.sale.order"].search(
            [("external_id", "=", external_id), ("backend_id", "=", self.backend.id)]
        )
        self.assertEqual(len(sale_order1), 1)

        self.assertTrue(sale_order1, "Woo Sale Order is not imported!")
        self.assertEqual(
            sale_order1.external_id, external_id, "External ID is different!!"
        )
        self.assertEqual(
            sale_order1.name,
            "WOO_71",
            "Order's name is not matched with response!",
        )
        self.assertEqual(
            sale_order1.woo_order_status_id.code,
            "processing",
            "Order's status is not matched with response!",
        )
        self.assertEqual(
            sale_order1.discount_total,
            -40.00,
            "Order's discount total is not matched with response!",
        )
        self.assertEqual(
            sale_order1.discount_tax,
            1.00,
            "Order's discount tax is not matched with response!",
        )
        self.assertEqual(
            sale_order1.shipping_total,
            10.00,
            "Order's shipping total is not matched with response!",
        )
        self.assertEqual(
            sale_order1.shipping_tax,
            1.00,
            "Order's shipping tax is not matched with response!",
        )
        self.assertEqual(
            sale_order1.cart_tax,
            0.00,
            "Order's cart tax is not matched with response!",
        )
        self.assertEqual(
            sale_order1.total_tax,
            0.00,
            "Order's total tax is not matched with response!",
        )
        self.assertEqual(
            sale_order1.woo_amount_total,
            50.00,
            "Order's woo amount total is not matched with response!",
        )
        self.assertEqual(
            sale_order1.woo_coupon,
            "flat50",
            "Order's woo amount total is not matched with response!",
        )
        sale_order1 = sale_order1.odoo_id
        sale_order1.action_confirm()
        delivery_order = sale_order1.picking_ids
        self.assertTrue(delivery_order, "Delivery order not created for the sale order")
        tracking_reference = "TR12345"
        delivery_order.write({"carrier_tracking_ref": tracking_reference})
        self.assertEqual(
            delivery_order.carrier_tracking_ref,
            tracking_reference,
            "Tracking reference not updated for the delivery order",
        )
        delivery_order.move_ids.quantity_done = 10
        delivery_order.button_validate()
        self.assertEqual(
            sale_order1.picking_ids.state, "done", "Picking state should be done!"
        )
        self.assertEqual(
            delivery_order.state,
            "done",
            "Delivery order should be in 'done' state after validation",
        )
        with recorder.use_cassette("export_woo_status_and_ref"):
            sale_order1.export_delivery_status()
        self.assertEqual(
            sale_order1.woo_order_status_id.code,
            "completed",
            "Sale Order is Not in 'Completed' state in WooCommerce.",
        )
