# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_br_edi.tests.test_l10n_br_edi import TestL10nBREDICommon
from odoo.tests import tagged

from odoo.addons.l10n_br_edi.tests.data_invoice_1 import invoice_1_submit_success_response as SUCCESSFUL_SUBMIT_RESPONSE
from .mocked_successful_status_response import RESPONSE as SUCCESSFUL_STATUS_RESPONSE


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBREDIServices(TestL10nBREDICommon):


    def test_l10n_br_edi_informative_taxes(self):
        rio_city = self.env.ref("l10n_br_avatax_services.br_city_rio_de_janeiro")
        self.invoice.invoice_line_ids.mapped("product_id").write(
            {
                "detailed_type": "service",
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

        with self.with_patched_account_move("_l10n_br_iap_request", SUCCESSFUL_SUBMIT_RESPONSE):
            self.wizard.action_send_and_print()

        informative_taxes = """Informative taxes:.*\
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
