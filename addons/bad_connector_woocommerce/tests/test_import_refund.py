from os.path import dirname, join

from vcr import VCR

from odoo.tests import Form

from .test_woo_backend import BaseWooTestCase

recorder = VCR(
    cassette_library_dir=join(dirname(__file__), "fixtures/cassettes"),
    decode_compressed_response=True,
    filter_headers=["Authorization"],
    path_transformer=VCR.ensure_suffix(".yaml"),
    record_mode="once",
)


class TestImportRefund(BaseWooTestCase):
    def setUp(self):
        """Setup configuration for Sale order refund2."""
        super().setUp()

    def test_import_order_for_refund(self):
        """Test Assertions for Import refund"""
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
        sale_order1 = sale_order1.odoo_id
        sale_order1.action_confirm()
        delivery_order = sale_order1.picking_ids
        self.assertTrue(delivery_order, "Delivery order not created for the sale order")
        delivery_order.move_ids[0].quantity_done = 1
        backorder_wizard_dict = delivery_order.button_validate()
        backorder_wizard = Form(
            self.env[backorder_wizard_dict["res_model"]].with_context(
                backorder_wizard_dict["context"]
            )
        ).save()
        backorder_wizard.process()
        sale_order_line = sale_order1.order_line.filtered(
            lambda line: line.product_id == delivery_order.move_ids[0].product_id
        )
        sale_order_line.product_id.qty_available = 2
        sale_order1.picking_ids[0].move_ids[0].quantity_done = 2
        sale_order1.picking_ids[0].button_validate()
        self.assertEqual(
            sale_order1.picking_ids[0].state,
            "done",
            "Picking state should be done!",
        )
        self.assertEqual(
            sale_order1.picking_ids[1].state,
            "done",
            "Picking state should be done!",
        )
        self.backend.process_return_automatically = False
        with recorder.use_cassette("import_woo_order_refund"):
            kwargs = {}
            kwargs["order_id"] = 71
            kwargs["refund_order_status"] = "refunded"
            self.env["woo.stock.picking.refund"].import_record(
                external_id="1481", backend=self.backend, **kwargs
            )
        return_picking = sale_order1.picking_ids.filtered(
            lambda picking: picking.woo_return_bind_ids
        )
        for picking in return_picking:
            for move in picking.move_ids:
                move.quantity_done = move.product_uom_qty
            picking.button_validate()
        self.assertEqual(
            sale_order1.woo_order_status_id.code,
            "refunded",
            "Sale Order is Not in 'Refunded' state in WooCommerce.",
        )
        self.assertEqual(len(sale_order1.picking_ids), 4)
