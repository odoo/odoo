# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import re
from contextlib import contextmanager
from unittest.mock import patch, DEFAULT

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.iap import InsufficientCreditError
from odoo.addons.l10n_br_edi.tests.data_invoice_1 import (
    invoice_1_request,
    invoice_1_submit_success_response,
    invoice_1_submit_fail_response,
    invoice_1_cancel_success_response,
    invoice_1_correct_success_response,
    invoice_1_correct_fail_response, invoice_1_cancel_fail_response,
)
from .mocked_successful_status_response import RESPONSE as SUCCESSFUL_STATUS_RESPONSE
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBREDICommon(TestAccountMoveSendCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('br')
    def setUpClass(cls):
        super().setUpClass()
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
        cls.invoice.is_tax_computed_externally = False  # FIXME hack to fix the fact the invoice was not posted before
        cls.invoice.action_post()
        cls.invoice.is_tax_computed_externally = True

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

    def test_l10n_br_edi_generate_and_send_single_wizard(self):
        single_wizard = self.env['account.move.send.wizard'].create({'move_id': self.invoice.id})
        self.assertEqual(single_wizard.sending_methods, ['email'])
        self.assertEqual(single_wizard.invoice_edi_format, False)
        self.assertTrue('br_edi' in single_wizard.extra_edis)
        with self.with_patched_account_move("_l10n_br_iap_request", invoice_1_submit_success_response):
            single_wizard.action_send_and_print()

    def test_l10n_br_edi_generate_and_send_batch_wizard(self):
        self.partner_customer.invoice_sending_method = 'manual'
        batch_wizard = self.env['account.move.send.batch.wizard'].create({'move_ids': self.invoice.ids})
        self.assertTrue(batch_wizard.summary_data)
        with self.with_patched_account_move("_l10n_br_iap_request", invoice_1_submit_success_response):
            batch_wizard.action_send_and_print()

    def test_l10n_br_edi_is_disabled(self):
        single_wizard = self.env['account.move.send.wizard'].create({'move_id': self.invoice.id, 'extra_edis': []})
        self.assertFalse(single_wizard.extra_edis)

        with self.with_patched_account_move("_l10n_br_iap_request") as patched_submit:
            single_wizard.action_send_and_print()

        self.assertFalse(patched_submit.called, "EDI should not have been called when the checkbox isn't checked.")

    def test_invoice_1_success(self):
        single_wizard = self.env['account.move.send.wizard'].create({'move_id': self.invoice.id})
        with self.with_patched_account_move("_l10n_br_iap_request", invoice_1_submit_success_response):
            single_wizard.action_send_and_print()

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
        single_wizard = self.env['account.move.send.wizard'].create({'move_id': self.invoice.id})
        with self.with_patched_account_move(
            "_l10n_br_iap_request", invoice_1_submit_fail_response
        ), self.assertRaisesRegex(UserError, re.escape(invoice_1_submit_fail_response["error"]["message"])):
            single_wizard.action_send_and_print()

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
        single_wizard = self.env['account.move.send.wizard'].create({'move_id': self.invoice.id})
        for Exc in (UserError, AccessError, InsufficientCreditError):
            with wrap_iap(Exc("test")):
                try:
                    single_wizard.action_send_and_print()
                finally:
                    self.invoice.l10n_br_last_edi_status = False

    def test_prepare_tax_data(self):
        to_include, header = self.invoice._l10n_br_edi_get_tax_data()

        for line in to_include["lines"]:
            for detail in line["taxDetails"]:
                self.assertFalse("ruleId" in detail and detail["ruleId"] is None, "ruleId shouldn't be sent when null.")

        self.assertEqual(header["goods"]["class"], "TEST CLASS VALUE", "Test class value should be included in header.")

    def test_update_cancel(self):
        self.invoice.button_draft()  # FIXME this test only works with a draft invoice, is it intended ?
        wizard = self.env["l10n_br_edi.invoice.update"].create(
            {"move_id": self.invoice.id, "mode": "cancel", "reason": "test reason with at least 15 characters"}
        )

        with self.with_patched_account_move("_l10n_br_iap_cancel_invoice_goods", invoice_1_cancel_success_response):
            wizard.action_submit()

        self.assertEqual(self.invoice.state, "cancel", "Invoice should be cancelled.")
        self.assertEqual(self.invoice.l10n_br_last_edi_status, "cancelled", "Invoice should be EDI cancelled.")

    def test_update_cancel_error(self):
        wizard = self.env["l10n_br_edi.invoice.update"].create(
            {"move_id": self.invoice.id, "mode": "cancel", "reason": "test reason with at least 15 characters"}
        )

        with self.with_patched_account_move("_l10n_br_iap_cancel_invoice_goods", invoice_1_cancel_fail_response), \
             self.assertRaisesRegex(UserError, "Rejei\u00e7\u00e3o: Evento n\u00e3o atende o Schema XML espec\u00edfico"):
            wizard.action_submit()

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


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBREDIServices(TestL10nBREDICommon):

    def test_l10n_br_edi_informative_taxes(self):
        rio_city = self.env.ref("l10n_br.city_br_002")
        self.invoice.invoice_line_ids.mapped("product_id").write(
            {
                "type": "service",
                "l10n_br_property_service_code_origin_id": self.env["l10n_br.service.code"].create(
                    {"code": "12345", "city_id": rio_city.id}
                ),
            }
        )
        self.invoice.partner_id.city_id = rio_city
        self.invoice.l10n_latam_document_type_id = self.env.ref("l10n_br.dt_SE")

        # Make sure we don't submit informative taxes
        payload = self.invoice._l10n_br_prepare_invoice_payload()
        self.assertTrue("informative" not in str(payload).lower())

        single_wizard = self.env['account.move.send.wizard'].create({'move_id': self.invoice.id})
        with self.with_patched_account_move("_l10n_br_iap_request", invoice_1_submit_success_response):
            single_wizard.action_send_and_print()

        informative_taxes = """Informative taxes:.*\
subtotalTaxable: 446.11, tax: 11.11, taxType: icmsDeson.*\
subtotalTaxable: 435, tax: 58.51, taxType: aproxtribFed.*\
subtotalTaxable: 435, tax: 82.65, taxType: aproxtribState.*\
subtotalTaxable: 435, tax: 0, taxType: ipi"""
        self.assertRegex(self.invoice.message_ids[-2].body, informative_taxes)

    def test_l10n_br_edi_service_status_successful(self):
        self.assertFalse(self.invoice.invoice_pdf_report_id, "PDF should not yet be generated.")
        self.invoice.l10n_br_last_edi_status = "pending"
        with self.with_patched_account_move("_l10n_br_iap_request", SUCCESSFUL_STATUS_RESPONSE):
            self.invoice.button_l10n_br_edi_get_service_invoice()

        self.assertEqual(self.invoice.l10n_br_last_edi_status, "accepted", "Invoice should be accepted.")
        self.assertTrue(self.invoice.invoice_pdf_report_id, "PDF should have been saved.")
        self.assertTrue(self.invoice.l10n_br_edi_xml_attachment_id, "XML should have been saved.")

    def test_update_cancel_accepted_invoice(self):
        """
        Test that cancelling an accepted posted invoice correctly sets EDI status to 'cancelled'.
        """
        # Simulate the real-world flow: invoice is posted and accepted
        self.invoice.l10n_br_last_edi_status = "accepted"
        self.invoice.l10n_br_access_key = "12345678901234567890123456789012345678901234"
        self.assertEqual(self.invoice.state, "posted", "Invoice should be posted.")
        self.assertEqual(self.invoice.l10n_br_last_edi_status, "accepted", "Invoice should be accepted.")

        # Create cancellation wizard
        wizard = self.env["l10n_br_edi.invoice.update"].create(
            {"move_id": self.invoice.id, "mode": "cancel", "reason": "test reason with at least 15 characters"}
        )

        # Submit cancellation
        with self.with_patched_account_move("_l10n_br_iap_cancel_invoice_goods", invoice_1_cancel_success_response):
            wizard.action_submit()

        # Verify the invoice is cancelled and EDI status is correctly set
        self.assertEqual(self.invoice.state, "cancel", "Invoice should be cancelled.")
        self.assertEqual(self.invoice.l10n_br_last_edi_status, "cancelled", "Invoice EDI status should be 'cancelled'")
