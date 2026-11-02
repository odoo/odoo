# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Tests for importing a supplier issued e-Tax Invoice / e-Receipt.

The inbound pipeline is exercised end to end: an outbound document is built
from a posted customer invoice (which is guaranteed XSD-valid), the resulting
XML is fed to :class:`od19.etax.import`, and the created Vendor Bill is checked
for the purchase journal, the vendor resolved from the TIN and the input VAT
(ภาษีซื้อ).
"""

import base64

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestOd19EtaxImport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.od19_etax_enabled = True
        cls.company.vat = "0105558000014"
        cls.buyer_vat = "0105551000001"
        cls.output_tax = cls.env["account.tax"].create({
            "name": "OD19 Test VAT Sale 7%",
            "amount": 7.0,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "price_include": False,
            "company_id": cls.company.id,
        })
        cls.input_tax = cls.env["account.tax"].create({
            "name": "OD19 Test VAT Purchase 7%",
            "amount": 7.0,
            "amount_type": "percent",
            "type_tax_use": "purchase",
            "price_include": False,
            "company_id": cls.company.id,
        })

    @classmethod
    def setup_independent_user(cls):
        """Keep the accounting groups of the test user (see role catalog)."""
        user = super().setup_independent_user()
        user.sudo().role_line_ids.unlink()
        user.sudo().write({
            "group_ids": [Command.set(cls.get_default_groups().ids)],
        })
        return user

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _vendor_xml(self, price_unit=1000.0, quantity=2.0):
        """Return a base64 XSD-valid XML issued by a fictional supplier."""
        invoice = self._create_invoice_one_line(
            product_id=self.product_a,
            price_unit=price_unit,
            quantity=quantity,
            tax_ids=self.output_tax,
            post=False,
        )
        invoice.action_post()
        # The buyer TIN is set after posting so the invoice is treated as an
        # abbreviated one: a full-form sale would require the Section 86/4
        # particulars (seller branch, buyer address) which are irrelevant here.
        invoice.partner_id.vat = self.buyer_vat
        document = self.env["od19.etax.document"].create({
            "move_id": invoice.id,
            "document_type": "tax_invoice",
        })
        document.action_generate_xml()
        return document.xml_file

    def _wizard(self, xml_file=None):
        return self.env["od19.etax.import"].create({
            "xml_file": xml_file if xml_file is not None else self._vendor_xml(),
            "xml_filename": "vendor-etax.xml",
        })

    def _blank_wizard(self):
        return self.env["od19.etax.import"].create({
            "xml_file": base64.b64encode(b"<xml/>"),
            "xml_filename": "dummy.xml",
        })

    @staticmethod
    def _remove_element(xml_file, local_name):
        root = etree.fromstring(base64.b64decode(xml_file))
        for child in list(root):
            if child.tag.rsplit("}", 1)[-1] == local_name:
                root.remove(child)
                break
        return base64.b64encode(etree.tostring(root))

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def test_parse_reads_the_received_document(self):
        wizard = self._wizard()
        wizard.action_parse()
        self.assertEqual(wizard.state, "parsed")
        self.assertEqual(wizard.document_type, "tax_invoice")
        self.assertTrue(wizard.document_reference)
        self.assertEqual(wizard.partner_vat, self.company.vat)
        self.assertEqual(wizard.buyer_vat, self.buyer_vat)
        self.assertTrue(wizard.invoice_date)
        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertAlmostEqual(line.quantity, 2.0)
        self.assertAlmostEqual(line.price_unit, 1000.0)
        self.assertAlmostEqual(line.tax_rate, 7.0)

    def test_parse_rejects_a_malformed_file(self):
        wizard = self.env["od19.etax.import"].create({
            "xml_file": base64.b64encode(b"<not-xml"),
            "xml_filename": "bad.xml",
        })
        with self.assertRaises(UserError):
            wizard.action_parse()
        self.assertEqual(wizard.state, "draft")

    def test_parse_rejects_a_non_etax_document(self):
        payload = base64.b64encode(b"<?xml version='1.0'?><root/>")
        wizard = self._wizard(payload)
        with self.assertRaises(UserError):
            wizard.action_parse()

    def test_parse_rejects_a_schema_violation(self):
        broken = self._remove_element(
            self._vendor_xml(), "SupplyChainTradeTransaction"
        )
        wizard = self._wizard(broken)
        with self.assertRaises(UserError):
            wizard.action_parse()

    # ------------------------------------------------------------------
    # Vendor resolution
    # ------------------------------------------------------------------
    def test_buyer_is_own_company_detection(self):
        wizard = self._blank_wizard()
        self.assertFalse(
            wizard._addressed_to_company({"tax_id": self.buyer_vat})
        )
        self.assertTrue(
            wizard._addressed_to_company({"tax_id": self.company.vat})
        )

    def test_vendor_is_resolved_by_tax_id(self):
        vendor = self.env["res.partner"].create({
            "name": "Existing Vendor",
            "vat": "0105559999996",
            "supplier_rank": 1,
        })
        wizard = self._blank_wizard()
        partner = wizard._resolve_vendor({
            "name": "Existing Vendor",
            "tax_id": "0105559999996",
        })
        self.assertEqual(partner, vendor)

    def test_vendor_is_created_when_unknown(self):
        wizard = self._blank_wizard()
        partner = wizard._resolve_vendor({
            "name": "Brand New Vendor",
            "tax_id": "0105551234567",
        }, create=True)
        self.assertTrue(partner)
        self.assertEqual(partner.vat, "0105551234567")
        self.assertEqual(partner.supplier_rank, 1)

    # ------------------------------------------------------------------
    # Vendor Bill creation
    # ------------------------------------------------------------------
    def test_import_requires_a_previous_parse(self):
        wizard = self._wizard()
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_import_creates_vendor_bill_with_input_vat(self):
        wizard = self._wizard()
        wizard.action_parse()
        wizard.action_import()
        move = wizard.move_id
        self.assertTrue(move)
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(move.partner_id.vat, self.company.vat)
        self.assertEqual(move.journal_id.type, "purchase")
        self.assertEqual(len(move.invoice_line_ids), 1)
        line = move.invoice_line_ids
        self.assertAlmostEqual(line.quantity, 2.0)
        self.assertAlmostEqual(line.price_unit, 1000.0)
        self.assertEqual(line.tax_ids, self.input_tax)
        self.assertAlmostEqual(move.amount_untaxed, 2000.0, places=2)
        self.assertAlmostEqual(move.amount_tax, 140.0, places=2)
        self.assertAlmostEqual(move.amount_total, 2140.0, places=2)

    def test_import_cannot_be_replayed(self):
        wizard = self._wizard()
        wizard.action_parse()
        wizard.action_import()
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_source_xml_is_attached_to_the_bill(self):
        wizard = self._wizard()
        wizard.action_parse()
        wizard.action_import()
        names = wizard.move_id.message_ids.mapped("attachment_ids.name")
        self.assertIn("vendor-etax.xml", names)
