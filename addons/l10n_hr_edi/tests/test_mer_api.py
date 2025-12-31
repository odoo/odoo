"""
These are LIVE tests of the MojEracun API (demo server).
Early inbox documents used for direct testing: 3084664, 3084663, 3084656, 3083666, 3082259
# First two have broken taxes, last two have a proper HR tax
# All five have scuffed company setup
"""

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_hr_edi.tests.test_hr_edi_common import TestL10nHrEdiCommon
from ..tools import (
    _mer_api_query_document_process_status_outbox,
    _mer_api_receive_document,
)


@tagged('external', 'external_l10n', 'post_install', '-post_install_l10n', '-at_install', '-standard')
class TestL10nHrEdiMerApi(TestL10nHrEdiCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'l10n_hr_mer_connection_mode': 'test',
            'l10n_hr_mer_username': '12513',
            'l10n_hr_mer_password': 'AeXLoJf9Ld',
            'l10n_hr_mer_company_ident': 'BE0477472701',
            'l10n_hr_mer_software_ident': 'Test-002',
        })
        cls.env.company._l10n_hr_activate_mojeracun()

    def _test_mer_api_send(self):
        """
        Test sending generated invoice through MER, bypassing most of the `account.move.send` flow.
        WARNING: permanently changes the state of the demo server!
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_mirror(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })

        moves_data = {move.sudo(): {**self.env['account.move.send']._get_default_sending_settings(move)} for move in [invoice]}
        self.env['account.move.send']._generate_invoice_documents(moves_data, allow_fallback_pdf=False)

        self.assertRecordValues(invoice, [{
            'l10n_hr_mer_document_status': '20',
        }])
        self.assertNotEqual(invoice.l10n_hr_mer_document_eid, False)

    def _test_mer_flow_send(self):
        """
        Test sending generated invoice through MER using the normal `account.move.send` flow.
        WARNING: permanently changes the state of the demo server!
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_mirror(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })

        send_and_print = self.create_send_and_print(invoice)
        send_and_print._generate_and_send_invoices(invoice)

        self.assertRecordValues(invoice, [{
            'l10n_hr_mer_document_status': '20',
        }])
        self.assertNotEqual(invoice.l10n_hr_mer_document_eid, False)

    def test_mer_api_query_document_process_status_outbox(self):
        """
        Test querying MER for statuse of an outbox document.
        """
        electronic_id = '3120260'
        response = _mer_api_query_document_process_status_outbox(
            self.env.company,
            electronic_id=electronic_id,
            status_id=None,
            invoice_year=None,
            invoice_number=None,
            date_from=None,
            date_to=None,
            by_update_date=None
        )
        self.assertEqual(response[0], {
            'ElectronicId': 3120260,
            'DocumentNr': '3/1/1',
            'DocumentTypeId': 1,
            'DocumentTypeName': 'Račun',
            'StatusId': 40,
            'StatusName': 'Preuzet',
            'OutboundFiscalizationStatus': None,
            'ReceiverBusinessNumber': 'BE0477472701',
            'ReceiverBusinessUnit': '',
            'ReceiverBusinessName': 'Odoo S.A.',
            'Created': '2025-12-11T13:06:20.3779916',
            'Updated': '2025-12-11T13:08:42.2070931',
            'IssueDate': '2025-12-11T00:00:00',
            'Sent': '2025-12-11T13:06:20.7546287',
            'Delivered': '2025-12-11T13:08:42.207087',
            'DocumentProcessStatusId': 4,
            'DocumentProcessStatusName': 'Potvrda zaprimanja',
            'AdditionalDokumentStatusId': None,
            'RejectReason': None
        })

    def test_mer_api_receive(self):
        """
        Test recieving a document with known MER ElectronicId from the MER system and importing it.
        Invoices sent to the demo server are returned as vendor bills.
        """
        electronic_id = '3120260'
        response = _mer_api_receive_document(
            self.env.company,
            electronic_id=electronic_id
        )
        self.assertEqual(response[:100], b'<?xml version="1.0" encoding="Utf-8" standalone="no"?><Invoice xmlns="urn:oasis:names:specification:')
        attachment = self.env["ir.attachment"].create({
                "name": f'mojeracun_{electronic_id}_attachment.xml',
                "raw": response,
                "type": "binary",
                "mimetype": "application/xml",
            })
        move = self.env.company._l10n_hr_mer_import_invoice(
            attachment,
            {
                'mer_document_eid': electronic_id,
                'mer_document_status': '40',
                'business_document_status': '0',
                'fiscalization_status': '0',
                'fiscalization_channel_type': '0',
            }
        )
        self.assertEqual(
            [
                move.invoice_date.strftime("%Y-%m-%d"),
                move.partner_id.name,
                move.amount_total,
                move.invoice_line_ids.product_id.name,
                move.l10n_hr_process_type,
                move.l10n_hr_fiscalization_number,
                move.line_ids[0].tax_ids,
                move.line_ids[0].l10n_hr_kpd_category_id.name,
            ],
            [
                '2025-12-11',
                'HR Company',
                4000.0,
                'Large Cabinet',
                'P1',
                '3/1/1',
                self.env['account.chart.template'].ref('VAT_P_IN_ROC_25'),  # The tax is flipped to purchase
                '31.00.12',
            ]
        )

    # Currently would break because of random test responses from fiscalization API, relies on a test exemption in the code
    def test_mer_flow_get_new_documents(self):
        """
        Test the flow of getting new documents from the MER server.
        For testing purposes, this is set up to fetch all the documents present rather than only
        the 'new' ones, allowing the test to be rerun successfully with no server changes,
        and to not notify MER of successful document import.
        Only a select number of 'trusted' documents are imported to avoid dragging the test out.
        """
        self.env.company._l10n_hr_mer_get_new_documents(
            undelivered_only=False,
            slc=(10, 20),  # Documents 3107515, 3110637, 3110651, 3111902, 3111911, 3114870, 3120196, 3120260, 3120276, 3120289
        )[self.env.company.id]
        moves = self.env['account.move'].search([('l10n_hr_mer_document_eid', '!=', False)])
        for move in moves:
            self.assertNotEqual(move.invoice_date, False)
            self.assertNotEqual(move.partner_id, False)
            self.assertNotEqual(move.amount_total, 0.0)
            self.assertNotEqual(move.invoice_line_ids.product_id, False)
            self.assertNotEqual(move.line_ids, False)
            self.assertNotEqual(move.l10n_hr_process_type, False)
            self.assertNotEqual(move.l10n_hr_fiscalization_number, False)
            self.assertEqual(any(line.l10n_hr_kpd_category_id for line in move.line_ids), True)

    # Currently results in random responses form the test server, cannot be set up to be tested properly
    # NEEDS TO BE REWRITTEN FOR THE UPDATED PAYMENT FLOW
    def test_mer_flow_report_payment(self):
        """
        Test reporting a payment for a document within the MER system.
        First create a partial payment for the document, then add the remaining payment.
        WARNING: permanently changes the state of the demo server!
        """
        electronic_id = '3084663'
        response = _mer_api_receive_document(
            self.env.company,
            electronic_id=electronic_id
        )
        attachment = self.env["ir.attachment"].create({
                "name": f'mojeracun_{electronic_id}_attachment.xml',
                "raw": response,
                "type": "binary",
                "mimetype": "application/xml",
            })
        move = self.env.company._l10n_hr_mer_import_invoice(
            attachment,
            {
                'mer_document_eid': electronic_id,
                'mer_document_status': '40',
                'business_document_status': '0',
                'fiscalization_status': '0',
                'fiscalization_channel_type': '0',
            }
        )
        move.action_post()

        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'amount': 25,
            'payment_date': move.date,
        })._create_payments()
        # We can't actually check anything other than the action failing in a predictable way
        # because test server responce for this API endpoint is random
        try:
            move.l10n_hr_edi_mer_action_report_paid()
        except UserError as e:
            if 'Error handling request:' in e.args:
                pass
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'amount': 100,
            'payment_date': move.date,
        })._create_payments()
        try:
            move.l10n_hr_edi_mer_action_report_paid()
        except UserError as e:
            if 'Error handling request:' in e.args:
                pass
