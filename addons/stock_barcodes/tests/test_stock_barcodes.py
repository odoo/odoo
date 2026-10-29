# Copyright 2108-2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import tagged

from .common import TestCommonStockBarcodes


@tagged("post_install", "-at_install")
class TestStockBarcodes(TestCommonStockBarcodes):
    def test_wizard_scan_location(self):
        self.action_barcode_scanned(self.wiz_scan, "8411322222568")
        self.assertEqual(self.wiz_scan.location_id, self.location_1)

    def test_wizard_scan_product(self):
        self.wiz_scan.location_id = self.location_1
        self.wiz_scan.action_show_step()
        self.action_barcode_scanned(self.wiz_scan, "8480000723208")
        self.assertEqual(self.wiz_scan.product_id, self.product_wo_tracking)
        self.assertEqual(self.wiz_scan.product_qty, 1.0)

    def test_wizard_scan_product_manual_entry(self):
        # Test manual entry
        self.wiz_scan.manual_entry = True
        self.wiz_scan.location_id = self.location_1
        self.wiz_scan.action_show_step()
        self.action_barcode_scanned(self.wiz_scan, "8480000723208")
        self.assertEqual(self.wiz_scan.product_qty, 0.0)
        self.wiz_scan.product_qty = 50.0

    def test_wizard_scan_package(self):
        self.wiz_scan.location_id = self.location_1
        self.wiz_scan.action_show_step()
        self.action_barcode_scanned(self.wiz_scan, "5420008510489")
        self.assertEqual(self.wiz_scan.product_id, self.product_tracking)
        self.assertEqual(self.wiz_scan.product_qty, 5.0)
        self.assertEqual(
            self.wiz_scan.packaging_id, self.product_tracking.packaging_ids
        )

        # Manual entry
        self.wiz_scan.manual_entry = True
        self.wiz_scan.action_clean_values()
        self.action_barcode_scanned(self.wiz_scan, "5420008510489")
        self.assertEqual(self.wiz_scan.packaging_qty, 0.0)
        self.wiz_scan.packaging_qty = 3.0
        self.wiz_scan.onchange_packaging_qty()
        self.assertEqual(self.wiz_scan.product_qty, 15.0)
        self.wiz_scan.manual_entry = False

    def test_wizard_scan_lot(self):
        self.wiz_scan.location_id = self.location_1.id
        self.wiz_scan.action_show_step()
        self.action_barcode_scanned(self.wiz_scan, "8411822222568")
        # Lot found for one product, so product_id is filled
        self.assertTrue(self.wiz_scan.product_id)
        self.action_barcode_scanned(self.wiz_scan, "8433281006850")
        self.action_barcode_scanned(self.wiz_scan, "8411822222568")
        self.assertEqual(self.wiz_scan.lot_id, self.lot_1)
        # After scan other product, set wizard lot to False
        self.action_barcode_scanned(self.wiz_scan, "8480000723208")
        self.assertFalse(self.wiz_scan.lot_id)

    def test_wizard_scan_not_found(self):
        self.action_barcode_scanned(self.wiz_scan, "84118xxx22568")
        self.assertEqual(
            self.wiz_scan.message,
            "84118xxx22568 (Barcode not found with this screen values)",
        )

    def test_wiz_clean_lot(self):
        self.wiz_scan.location_id = self.location_1.id
        self.wiz_scan.action_show_step()
        self.action_barcode_scanned(self.wiz_scan, "8433281006850")
        self.action_barcode_scanned(self.wiz_scan, "8411822222568")
        self.wiz_scan.action_clean_lot()
        self.assertFalse(self.wiz_scan.lot_id)
