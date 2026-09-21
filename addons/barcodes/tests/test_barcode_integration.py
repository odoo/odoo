"""Tests for the parts of the module that are not the parser.

The nomenclature/company wiring and the events mixin had no coverage at all,
which is how a nomenclature could be deleted out from under the company using
it without anything noticing.
"""

from odoo.exceptions import UserError
from odoo.tests import common


class TestBarcodeNomenclatureLifecycle(common.TransactionCase):
    def test_default_nomenclature_cannot_be_deleted(self):
        default = self.env.ref("barcodes.default_barcode_nomenclature")
        with self.assertRaises(UserError):
            default.unlink()

    def test_nomenclature_in_use_cannot_be_deleted(self):
        """Deleting it used to empty `company.barcodes_config_id.nomenclature_id` silently.

        `ondelete` defaults to "set null", so nothing raised -- and every later
        scan parsed against no rules and came back `type: "error"` with nothing
        pointing at the deletion.
        """
        nomenclature = self.env["barcode.nomenclature"].create({"name": "In Use"})
        self.env.company.barcodes_config_id.nomenclature_id = nomenclature
        with self.assertRaises(UserError):
            nomenclature.unlink()
        self.assertEqual(
            self.env.company.barcodes_config_id.nomenclature_id, nomenclature
        )

    def test_unused_nomenclature_can_be_deleted(self):
        nomenclature = self.env["barcode.nomenclature"].create({"name": "Unused"})
        nomenclature.unlink()
        self.assertFalse(nomenclature.exists())

    def test_new_company_gets_the_default_nomenclature(self):
        company = self.env["res.company"].create({"name": "Barcode Co"})
        self.assertEqual(
            company.barcodes_config_id.nomenclature_id,
            self.env.ref("barcodes.default_barcode_nomenclature"),
        )


class TestBarcodeEventsMixin(common.TransactionCase):
    def test_unimplemented_hook_raises_for_the_developer(self):
        """A model inheriting the mixin without the hook fails loudly, and the
        message names the model rather than being a translated string aimed at
        an end user who will never see it."""
        scanned = self.env["mixin.barcodes.barcode_events"]
        with self.assertRaises(NotImplementedError) as caught:
            scanned.on_barcode_scanned("12345670")
        self.assertIn("mixin.barcodes.barcode_events", str(caught.exception))

    def test_onchange_clears_the_field_and_forwards_the_barcode(self):
        """The carrier field must be emptied, or the next identical scan is a
        no-op: the onchange would not fire for an unchanged value."""
        seen = []
        mixin = self.env["mixin.barcodes.barcode_events"]
        record = mixin.new({"_barcode_scanned": "12345670"})
        self.patch(
            type(mixin),
            "on_barcode_scanned",
            lambda self, barcode: seen.append(barcode),
        )
        record._on_barcode_scanned()
        self.assertEqual(seen, ["12345670"])
        self.assertEqual(record._barcode_scanned, "")

    def test_onchange_ignores_an_empty_barcode(self):
        seen = []
        mixin = self.env["mixin.barcodes.barcode_events"]
        record = mixin.new({"_barcode_scanned": ""})
        self.patch(
            type(mixin),
            "on_barcode_scanned",
            lambda self, barcode: seen.append(barcode),
        )
        self.assertIsNone(record._on_barcode_scanned())
        self.assertEqual(seen, [])
