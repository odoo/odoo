from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_tr_nilvera_einvoice_extended.tests.test_xml_ubl_tr import TestUBLTR


@tagged("post_install_l10n", "post_install", "-at_install")
class TestUBLTRGibInvoiceScenarios(TestUBLTR):
    def _generate_invoice(self, partner_id, tax=None, **kwargs):
        invoice_tax = (tax and tax.ids) or self.tax_20.ids
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "company_id": self.company_data["company"].id,
                "partner_id": partner_id.id,
                "name": "EIN/2025/1",
                "invoice_date": "2025-03-03",
                "narration": "3 products",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 50.00,
                            "quantity": 3,
                            "discount": 12,
                            "tax_ids": [Command.set(invoice_tax)],
                        }
                    ),
                ],
                **kwargs,
            }
        )
        invoice.action_post()
        return invoice

    def _generate_invoice_xml(self, partner_id, tax=None, include_invoice=False, **kwargs):
        invoice = self._generate_invoice(partner_id, tax, **kwargs)
        if include_invoice:
            return self.env["account.edi.xml.ubl.tr"]._export_invoice(invoice)[0], invoice
        return self.env["account.edi.xml.ubl.tr"]._export_invoice(invoice)[0]

    def _generate_return_invoice_xml(self, partner_id, tax=None, **kwargs):
        invoice = self._generate_invoice(partner_id, tax, **kwargs)
        credit_note = invoice._reverse_moves()
        credit_note.action_post()
        return self.env["account.edi.xml.ubl.tr"]._export_invoice(credit_note)[0]

    def test_xml_invoice_basic_return_einvoice(self):
        with freeze_time("2025-03-05"):
            generated_xml = self._generate_return_invoice_xml(self.einvoice_partner)

        with file_open(
            "l10n_tr_gib_invoice_scenarios/tests/expected_xmls/invoice_basic_return_einvoice.xml", "rb"
        ) as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))

    def test_xml_invoice_basic_withholding_return_einvoice(self):
        with freeze_time("2025-03-05"):
            generated_xml = self._generate_return_invoice_xml(
                self.einvoice_partner, self.tax_20_withholding, l10n_tr_gib_invoice_type="TEVKIFAT"
            )

        with file_open(
            "l10n_tr_gib_invoice_scenarios/tests/expected_xmls/invoice_return_basic_withholding_einvoice.xml", "rb"
        ) as expected_xml_file:
            expected_xml = expected_xml_file.read()

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(generated_xml), self.get_xml_tree_from_string(expected_xml))
