import logging
import requests
from freezegun import freeze_time
from unittest.mock import patch
from unittest import mock

from odoo.tests.common import tagged
from odoo.tools import misc
from odoo import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install", "post_install_l10n")
class TestUyEdi(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('uy')
    def setUpClass(cls):
        super().setUpClass()
        cls.frozen_today = "2024-06-15T10:00:00"
        cls.env.ref("base.lang_es_UY").active = True

        cls.company_data["company"].write({
            "name": "(UY) Uruguay Company (Unit Tests)",
            "vat": "215521750017",
            "state_id": cls.env.ref("base.state_uy_10").id,
            "street": "Calle Falsa 254",
            "city": "Montevideo",
            "zip": "2000",
            "phone": "+1 555 123 8069",
            "email": "info@example.com",
            "website": "www.example.com",
        })
        cls.company_uy = cls.company_data["company"]
        cls.partner_local_tk = cls.env["res.partner"].create({
            "name": "IEB Internacional",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_uy.it_dni").id,
            "vat": "218435730016",
            "street": "Bach 0",
            "city": "Aeroparque",
            "state_id": cls.env.ref("base.state_uy_02").id,
            "country_id": cls.env.ref("base.uy").id,
            "email": "rut@example.com",
            "lang": "es_UY",
        })
        cls.partner_local = cls.env["res.partner"].create({
            "name": "IEB Internacional",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_uy.it_rut").id,
            "vat": "218435730016",
            "street": "Bach 0",
            "city": "Aeroparque",
            "state_id": cls.env.ref("base.state_uy_02").id,
            "country_id": cls.env.ref("base.uy").id,
            "email": "rut@example.com",
        })

        cls.foreign_partner = cls.env["res.partner"].create({
            "name": "Foreign Inc",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_latam_base.it_vat").id,
            "is_company": True,
            "vat": "17-2038053",
            "zip": "95380",
            "street": "7841 Red Road",
            "city": "San Francisco",
            "state_id": cls.env.ref("base.state_us_5").id,
            "country_id": cls.env.ref("base.us").id,
            "email": "foreing@example.com",
            "phone": "(123)-456-7890",
            "website": "http://www.foreign-inc.com",
        })
        cls.tax_22 = cls.env.ref("account.%s_vat1" % cls.company_uy.id)
        cls.tax_10 = cls.env.ref("account.%s_vat2" % cls.company_uy.id)
        cls.tax_0 = cls.env.ref("account.%s_vat3" % cls.company_uy.id)
        cls.reduced_tax = cls.env.ref("account.%s_vat11" % cls.company_uy.id)

        # Products
        cls.service_vat_22 = cls.env["product.product"].create({
            "name": "Virtual Home Staging (VAT 22)",
            "list_price": 38.25,
            "standard_price": 45.5,
            "type": "service",
            "default_code": "VAT 22",
            "taxes_id": [(6, 0, cls.tax_22.ids)],
        })
        cls.service_vat_10 = cls.env["product.product"].create({
            "name": "Service (VAT 10)",
            "list_price": 38.25,
            "standard_price": 45.5,
            "type": "service",
            "default_code": "VAT 10",
            "taxes_id": [(6, 0, cls.tax_10.ids)],
        })
        cls.service_reduced_vat = cls.env["product.product"].create({
            "name": "Virtual Home Staging (Reduced VAT)",
            "list_price": 38.25,
            "standard_price": 45.5,
            "type": "service",
            "default_code": "Reduced VAT",
            "taxes_id": [(6, 0, cls.reduced_tax.ids)],
        })
        cls.product_vat_22 = cls.env["product.product"].create({
            "name": "Customizable Desk (VAT 10)",
            "list_price": 38.25,
            "standard_price": 45.5,
            "type": "consu",
            "default_code": "product UY",
            "taxes_id": [(6, 0, cls.tax_22.ids)],
        })

        # Rates
        cls.env["res.currency.rate"].create({
            "name": "2024-05-08",
            "currency_id": cls.env.ref("base.USD").id,
            "rate": 0.02602066,
            "company_id": cls.company_uy.id,
        })
        cls.env["res.currency.rate"].create({
            "name": "2024-05-08",
            "currency_id": cls.env.ref("base.UYI").id,
            "rate": 0.1665806,
            "company_id": cls.company_uy.id,
        })

        cls.utils_path = "odoo.addons.l10n_uy_edi.models.l10n_uy_edi_document.L10nUyEdiDocument"
        cls.mocked_responses_path = "l10n_uy_edi/tests/responses/"
        cls.mocked_cfes_path = "l10n_uy_edi/tests/expected_cfes/"

    @classmethod
    def _create_move(cls, **kwargs):
        with freeze_time(cls.frozen_today, tz_offset=3):
            invoice = cls.env['account.move'].create({
                'partner_id': cls.partner_local_tk.id,
                'move_type': 'out_invoice',
                'journal_id': cls.company_data['default_journal_sale'].id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.service_vat_22.id,
                        'quantity': 1.0,
                        'price_unit': 100.0,
                    }),
                ],
                **kwargs,
            })
            invoice.invoice_date = invoice.date
        return invoice

    def _create_credit_note(self, invoice):
        with freeze_time(self.frozen_today, tz_offset=3):
            refund_wizard = self.env["account.move.reversal"].with_context({
                "active_ids": [invoice.id], "active_model": "account.move"}).create({
                    "reason": "Mercadería defectuosa",
                    "journal_id": invoice.journal_id.id,
                })
            res = refund_wizard.refund_moves()
        return self.env["account.move"].browse(res["res_id"])

    def _create_debit_note(self, invoice):
        with freeze_time(self.frozen_today, tz_offset=3):
            debit_note_wizard = self.env["account.debit.note"]\
                .with_context({"active_ids": [invoice.id], "active_model": "account.move", "default_copy_lines": True})\
                .create({"reason": "Mercadería defectuosa"})
            res = debit_note_wizard.create_debit()

        debit_note = self.env["account.move"].browse(res["res_id"])
        return debit_note

    def _mocked_response(self, response_file, exception=None):
        """ Read the xml response file, change it to dictionary and return the result """
        if response_file == "NO_RESPONSE" or not response_file:
            mock_response = None
        else:
            xml_content = misc.file_open(self.mocked_responses_path + response_file + ".xml", mode="rb").read()
            mock_response = mock.Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = ""
            mock_response.content = xml_content
        errors = [exception] if exception else []
        return self.env["l10n_uy_edi.document"]._process_response(mock_response, errors)

    def _mock_send_and_print(self, invoice, expected_xml_file, get_pdf=None, exception=None):
        inbox_patch = dict(
            target=f"{self.utils_path}._ucfe_inbox",
            return_value=self._mocked_response(expected_xml_file, exception=exception),
        )
        query_patch = dict(
            target=f"{self.utils_path}._ucfe_query",
            return_value=self._mocked_response(expected_xml_file + "_pdf" if get_pdf else False),
        )
        with patch(**inbox_patch), patch(**query_patch):
            self._send_and_print(invoice)

    def _mock_update_dgi_state(self, invoice, expected_xml_file):
        with patch(f"{self.utils_path}._ucfe_inbox", return_value=self._mocked_response(expected_xml_file + "_status")):
            invoice.l10n_uy_edi_action_update_dgi_state()

    def _mock_check_credentials(self, company, expected_xml_file):
        with patch(f"{self.utils_path}._ucfe_inbox", return_value=self._mocked_response(expected_xml_file)):
            error_msg = self.env["l10n_uy_edi.document"]._validate_credentials(company)
        return error_msg

    def _mock_cron_l10n_uy_edi_get_vendor_bills(self, expected_folder, get_pdf=False):
        """ Call the cron to create vendor bills, will simulate that we have a notification, we read it and process
        the info and pdf of the vendor bill and then will stop the cron because there ar not more notificactions """
        with patch(f"{self.utils_path}._ucfe_inbox") as mock_inbox, patch(f"{self.utils_path}._ucfe_query",
            return_value=self._mocked_response(expected_folder + '_pdf' if get_pdf else False)):
            mock_inbox.side_effect = [
                self._mocked_response(expected_folder + '/response_600'),  # Find if they are notifications available
                self._mocked_response(expected_folder + '/response_610'),  # Read the notification
                self._mocked_response(expected_folder + '/_status'),  # Update the status of the CFE
                self._mocked_response(expected_folder + '/response_620'),  # Discard Notification
                self._mocked_response(expected_folder + '/response_600_end'),  # No more notifications
            ]
            self.env["l10n_uy_edi.document"].cron_l10n_uy_edi_get_vendor_bills()

    def _send_and_print(self, invoice):
        self.env["account.move.send.wizard"] \
            .with_context(active_model=invoice._name, active_ids=invoice.ids) \
            .create({}) \
            .action_send_and_print()

    def _check_cfe(self, invoice, expected_prefix, expected_xml_file):
        self.assertEqual(invoice.name, "%s DE%07d" % (expected_prefix, invoice.id), "Not valid name")
        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "accepted", "CFE not accepted in demo mode not possible (it is always accepted)")
        expected_xml = self.get_xml_tree_from_string(misc.file_open(self.mocked_cfes_path + expected_xml_file + ".xml").read())
        result_xml = self.get_xml_tree_from_attachment(invoice.l10n_uy_edi_document_id.attachment_id)

        # For Debit/Credit Notes we need to change the original expected document to add the proper tag.
        ref_number = False
        if invoice.reversed_entry_id:
            ref_number = invoice.l10n_uy_edi_document_id._get_doc_parts(invoice.reversed_entry_id)[1]
        if invoice.debit_origin_id:
            ref_number = invoice.l10n_uy_edi_document_id._get_doc_parts(invoice.debit_origin_id)[1]
        if ref_number:
            namespace = {"cfe": "http://cfe.dgi.gub.uy"}
            expected_xml.find(".//cfe:Referencia/cfe:Referencia/cfe:NroCFERef", namespace).text = ref_number
        self.assertXmlTreeEqual(expected_xml, result_xml)

    def _mock_upload_document_on_journal(self, journal, filename):
        filename = filename + ".xml"
        content = misc.file_open("l10n_uy_edi/tests/sobres_from_uruware/" + filename, mode="rb").read()
        attachment = self.env['ir.attachment'].create({
            'raw': content,
            'name': filename,
        })
        with patch(f"{self.utils_path}._create_pdf_vendor_bill", return_value=None):
            action_vals = journal.create_document_from_attachment(attachment.ids)
        return self.env['account.move'].browse(action_vals['res_id'])

    def _configure_usd_company_currency(self):
        USD = self.env.ref("base.USD")
        UYU = self.env.ref("base.UYU")
        self.company_uy.currency_id = USD
        self.env["res.currency.rate"].search([('currency_id', '=', USD.id)]).unlink()
        self.env["res.currency.rate"].search([('currency_id', '=', UYU.id)]).unlink()

        rate_date = "2025-09-25"
        self.env["res.currency.rate"].create([
            {"name": rate_date, "company_id": self.company_uy.id, "currency_id": USD.id, "rate": 1.0},
            {"name": rate_date, "company_id": self.company_uy.id, "currency_id": UYU.id, "rate": 1.0 / 0.02602066},
        ])

        self.assertEqual(self.company_uy.currency_id, USD)
        self.assertEqual(self.company_uy.currency_id.rate, 1.0)
