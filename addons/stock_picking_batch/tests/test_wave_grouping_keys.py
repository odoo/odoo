from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWaveGroupingKeys(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.shelf = cls.env["stock.location"].create(
            {"name": "Wave key shelf", "location_id": cls.stock_location.id}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Wave key product", "is_storable": True}
        )
        cls.env["stock.quant"]._update_available_quantity(cls.product, cls.shelf, 100)
        cls.no_batch_grouping = dict.fromkeys(
            cls.env["stock.picking.type"]._get_batch_group_by_keys(), False
        )

    def _picking(self, picking_type, source, destination, partner=False):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "partner_id": partner and partner.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 3,
                            "partner_id": False,
                            "location_id": source.id,
                            "location_dest_id": destination.id,
                        }
                    )
                ],
            }
        )

    def _receipt_type_grouped_by_vendor(self):
        picking_type = self.env.ref("stock.picking_type_in")
        picking_type.write(
            {
                **self.no_batch_grouping,
                "auto_batch": True,
                "batch_group_by_partner": True,
                "wave_group_by_product": True,
            }
        )
        return picking_type

    def test_transfers_of_two_vendors_confirmed_together_get_a_wave_each(self):
        picking_type = self._receipt_type_grouped_by_vendor()
        vendor_b = self.env["res.partner"].create({"name": "Vendor B"})
        vendor_c = self.env["res.partner"].create({"name": "Vendor C"})
        receipts = self._picking(
            picking_type, self.supplier_location, self.stock_location, vendor_b
        ) | self._picking(
            picking_type, self.supplier_location, self.stock_location, vendor_c
        )
        self.assertFalse(
            receipts.move_ids.partner_id,
            "A receipt's moves carry no contact of their own, as a purchase "
            "order's do; the vendor lives on the transfer.",
        )
        receipts.action_confirm()
        self.assertEqual(len(receipts.batch_id), 2)
        for receipt in receipts:
            self.assertTrue(receipt.batch_id.is_wave)
            self.assertEqual(
                receipt.batch_id.picking_ids.partner_id, receipt.partner_id
            )

    def test_a_second_transfer_of_the_same_vendor_joins_its_wave(self):
        picking_type = self._receipt_type_grouped_by_vendor()
        vendor = self.env["res.partner"].create({"name": "Vendor A"})
        first = self._picking(
            picking_type, self.supplier_location, self.stock_location, vendor
        )
        first.action_confirm()
        second = self._picking(
            picking_type, self.supplier_location, self.stock_location, vendor
        )
        second.action_confirm()
        self.assertTrue(first.batch_id.is_wave)
        self.assertEqual(second.batch_id, first.batch_id)

    def test_lines_reserved_below_the_transfer_source_join_its_wave(self):
        picking_type = self.env.ref("stock.picking_type_out")
        picking_type.write(
            {
                **self.no_batch_grouping,
                "auto_batch": True,
                "batch_group_by_src_loc": True,
                "wave_group_by_product": True,
            }
        )
        first = self._picking(picking_type, self.stock_location, self.customer_location)
        first.action_confirm()
        second = self._picking(
            picking_type, self.stock_location, self.customer_location
        )
        second.action_confirm()
        self.assertEqual(
            (first | second).move_line_ids.location_id,
            self.shelf,
            "The transfers leave from the stock location, their lines from a "
            "shelf below it.",
        )
        self.assertTrue(first.batch_id.is_wave)
        self.assertEqual(second.batch_id, first.batch_id)
        self.assertEqual(first.batch_id.wave_source_location_id, self.stock_location)
