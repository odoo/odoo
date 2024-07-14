# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from contextlib import contextmanager
from unittest.mock import patch, DEFAULT

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.iap import InsufficientCreditError
from odoo.addons.l10n_br_edi.tests.data_invoice_1 import (
    invoice_1_request,
    invoice_1_submit_success_response,
    invoice_1_submit_fail_response,
    invoice_1_cancel_success_response,
    invoice_1_correct_success_response,
    invoice_1_correct_fail_response,
)
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tests import tagged
from odoo.tools import json


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBREDICommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="br"):
        super().setUpClass(chart_template_ref)
        company = cls.company_data["company"]
        company.partner_id.write(
            {
                "street": "Rua Marechal Deodoro",
                "street2": "Centro",
                "city": "Curitaba",
                "state_id": cls.env.ref("base.state_br_pr").id,
                "zip": "80010-010",
                "country_id": cls.env.ref("base.br").id,
                "vat": "49233848000150",
                "l10n_br_ie_code": "9102799558",
            }
        )
        cls.partner_customer = cls.env["res.partner"].create(
            {
                "name": "BR Company Customer",
                "street": "Av. Presidente Vargas 592",
                "street2": "Centros",
                "city": "Rio de Janeiro",
                "state_id": cls.env.ref("base.state_br_rj").id,
                "zip": "20071-001",
                "vat": "51494569013170",
            }
        )

        cls.product_screens = cls.env["product.template"].create(
            {
                "name": "Acoustic Bloc Screens",
                "list_price": 295.00,
                "default_code": "FURN_6666",
                "l10n_br_ncm_code_id": cls.env.ref("l10n_br_avatax.49011000").id,
                "l10n_br_source_origin": "0",
                "l10n_br_sped_type": "FOR PRODUCT",
                "l10n_br_use_type": "use or consumption",
            }
        )
        cls.product_cabinet = cls.env["product.template"].create(
            {
                "name": "Cabinet with Doors",
                "list_price": 140.00,
                "default_code": "E-COM11",
                "l10n_br_ncm_code_id": cls.env.ref("l10n_br_avatax.49011000").id,
                "l10n_br_source_origin": "0",
                "l10n_br_sped_type": "FOR PRODUCT",
                "l10n_br_use_type": "use or consumption",
            }
        )

        cls.avatax_fp = cls.env["account.fiscal.position"].create({"name": "Avatax Brazil", "l10n_br_is_avatax": True})

        cls.invoice = cls.env["account.move"].create(
            {
                "partner_id": cls.partner_customer.id,
                "move_type": "out_invoice",
                "invoice_date": "2023-10-05",
                "currency_id": cls.env.ref("base.BRL").id,
                "fiscal_position_id": cls.avatax_fp.id,
                "l10n_br_edi_avatax_data": json.dumps(
                    {
                        "header": invoice_1_request["header"],
                        "lines": invoice_1_request["lines"],
                        "summary": invoice_1_request["summary"],
                    }
                ),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {"product_id": cls.product_screens.product_variant_id.id},
                    ),
                    (
                        0,
                        0,
                        {"product_id": cls.product_cabinet.product_variant_id.id},
                    ),
                ],
            }
        )
        cls.wizard = cls.env["account.move.send"].create({"move_ids": cls.invoice.ids})

    @contextmanager
    def with_patched_account_move(self, method_name, mocked_response=None):
        with patch.object(
            type(self.env["account.move"]),
            method_name,
            new=(lambda *args, **kwargs: mocked_response) if mocked_response is not None else DEFAULT,
            autospec=not mocked_response,
        ) as patched_fn:
            yield patched_fn


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBREDI(TestL10nBREDICommon):
    def test_l10n_br_edi_is_enabled_checkbox(self):
        self.wizard.l10n_br_edi_is_enabled = False
        self.wizard.checkbox_download = False

        with self.with_patched_account_move("_l10n_br_iap_submit_invoice_goods") as patched_submit:
            self.wizard.action_send_and_print()

        self.assertFalse(patched_submit.called, "EDI should not have been called when the checkbox isn't checked.")

    def test_invoice_1_success(self):
        with self.with_patched_account_move("_l10n_br_iap_submit_invoice_goods", invoice_1_submit_success_response):
            self.wizard.action_send_and_print()

        self.assertEqual(self.invoice.l10n_br_last_edi_status, "accepted", "The EDI document should be accepted.")
        self.assertEqual(
            self.invoice.invoice_pdf_report_file.decode(),
            invoice_1_submit_success_response["pdf"]["base64"],
            "PDF data should have been saved on the EDI document.",
        )
        self.assertEqual(
            self.invoice.l10n_br_edi_xml_attachment_id.datas.decode(),
            invoice_1_submit_success_response["xml"]["base64"],
            "XML data should have been saved on the EDI document.",
        )
        self.assertEqual(
            self.invoice.l10n_br_access_key,
            invoice_1_submit_success_response["key"],
            "The access key should have been saved.",
        )
        self.assertFalse(self.invoice.l10n_br_edi_avatax_data, "Saved Avatax tax data should have been removed.")

    def test_invoice_1_fail(self):
        with self.with_patched_account_move(
            "_l10n_br_iap_submit_invoice_goods", invoice_1_submit_fail_response
        ), self.assertRaisesRegex(UserError, re.escape(invoice_1_submit_fail_response["error"]["message"])):
            self.wizard.action_send_and_print()

        self.assertEqual(self.invoice.l10n_br_last_edi_status, "error", "The EDI document should be in error.")
        self.assertFalse(
            self.invoice.invoice_pdf_report_file,
            "There should be no PDF data on the EDI document.",
        )
        self.assertFalse(
            self.invoice.l10n_br_edi_xml_attachment_id,
            "There should be no XML data on the EDI document.",
        )
        self.assertTrue(self.invoice.l10n_br_edi_avatax_data, "Saved Avatax tax data should have been kept.")

    def test_invoice_1_iap_errors(self):
        """Test that we properly catch errors from IAP. We should never raise, because it would break the asynchronous
        invoice_multi mode. We can't test the asynchronous mode easily, but we can test if we catch IAP errors by looking
        at their format."""
        @contextmanager
        def wrap_iap(exception):
            # If the error is prefixed with "Errors when..." we know we caught and handled it.
            with patch(
                "odoo.addons.l10n_br_avatax.models.account_external_tax_mixin.iap_jsonrpc", side_effect=exception
            ), self.assertRaisesRegex(UserError, "Errors when submitting the e-invoice:"):
                yield

        for Exc in (UserError, AccessError, InsufficientCreditError):
            with wrap_iap(Exc("test")):
                try:
                    self.wizard.action_send_and_print()
                finally:
                    self.wizard.move_ids.l10n_br_last_edi_status = False

    def test_prepare_tax_data(self):
        to_include, header = self.invoice._l10n_br_edi_get_tax_data()

        for line in to_include["lines"]:
            for detail in line["taxDetails"]:
                self.assertFalse("ruleId" in detail and detail["ruleId"] is None, "ruleId shouldn't be sent when null.")

        self.assertEqual(header["goods"]["class"], "TEST CLASS VALUE", "Test class value should be included in header.")

    def test_update_cancel(self):
        wizard = self.env["l10n_br_edi.invoice.update"].create(
            {"move_id": self.invoice.id, "mode": "cancel", "reason": "test reason"}
        )

        with self.with_patched_account_move("_l10n_br_iap_cancel_invoice_goods", invoice_1_cancel_success_response):
            wizard.action_submit()

        self.assertEqual(self.invoice.state, "cancel", "Invoice should be cancelled.")
        self.assertEqual(self.invoice.l10n_br_last_edi_status, "cancelled", "Invoice should be EDI cancelled.")

    def test_update_correction(self):
        wizard = self.env["l10n_br_edi.invoice.update"].create(
            {"move_id": self.invoice.id, "mode": "correct", "reason": "Reason to make this correction."}
        )

        self.assertFalse(
            self.invoice.l10n_br_edi_last_correction_number, "Invoice shouldn't have a correction number yet (is 0)."
        )
        original_state = self.invoice.state
        original_edi_state = self.invoice.l10n_br_last_edi_status
        with self.with_patched_account_move("_l10n_br_iap_correct_invoice_goods", invoice_1_correct_success_response):
            wizard.action_submit()

        self.assertEqual(self.invoice.state, original_state, "Invoice state shouldn't have changed.")
        self.assertEqual(
            self.invoice.l10n_br_last_edi_status, original_edi_state, "Invoice EDI state shouldn't have changed."
        )
        self.assertEqual(self.invoice.l10n_br_edi_last_correction_number, 1, "Latest correction number should be 1")

    def test_update_correction_error(self):
        # This will fail because the reason must be >=15 characters according to Avalara.
        wizard = self.env["l10n_br_edi.invoice.update"].create(
            {"move_id": self.invoice.id, "mode": "correct", "reason": "Too short."}
        )

        with self.with_patched_account_move(
            "_l10n_br_iap_correct_invoice_goods", invoice_1_correct_fail_response
        ), self.assertRaisesRegex(ValidationError, re.escape(invoice_1_correct_fail_response["status"]["desc"])):
            wizard.action_submit()

    def test_new_invoice_attachments(self):
        """Test that newly set invoice PDFs or XMLs are reflected in the fields."""
        def set_new_attachments(invoice, response):
            new_attachments = invoice._l10n_br_edi_attachments_from_response(response)
            new_pdf_attachment = new_attachments.filtered(lambda attachment: ".pdf" in attachment.name)
            new_xml_attachment = new_attachments.filtered(lambda attachment: ".xml" in attachment.name)

            self.assertEqual(invoice.invoice_pdf_report_id, new_pdf_attachment)
            self.assertEqual(invoice.l10n_br_edi_xml_attachment_id, new_xml_attachment)
            self.assertEqual(invoice.message_main_attachment_id, new_pdf_attachment)

        set_new_attachments(self.invoice, invoice_1_submit_success_response)
        set_new_attachments(self.invoice, invoice_1_submit_success_response)
