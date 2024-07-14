# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import textwrap
import unittest

from odoo import fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.iap_extract.tests.test_extract_mixin import TestExtractMixin
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged
from odoo.tools import file_open

from ..models.account_invoice import OCR_VERSION


@tagged('post_install', '-at_install')
class TestInvoiceExtract(AccountTestInvoicingCommon, TestExtractMixin, MailCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id |= cls.env.ref('base.group_system')

        # Required for `price_total` to be visible in the view
        config = cls.env['res.config.settings'].create({})
        config.execute()

        cls.journal_with_alias = cls.env['account.journal'].search(
            [('company_id', '=', cls.env.user.company_id.id), ('type', '=', 'sale')],
            limit=1,
        )

    def get_result_success_response(self):
        return {
            'results': [{
                'client': {'selected_value': {'content': "Test"}, 'candidates': []},
                'supplier': {'selected_value': {'content': "Test"}, 'candidates': []},
                'total': {'selected_value': {'content': 330}, 'candidates': []},
                'subtotal': {'selected_value': {'content': 300}, 'candidates': []},
                'invoice_id': {'selected_value': {'content': 'INV0001'}, 'candidates': []},
                'total_tax_amount': {'selected_value': {'content': 30.0}, 'words': []},
                'currency': {'selected_value': {'content': 'EUR'}, 'candidates': []},
                'VAT_Number': {'selected_value': {'content': 'BE0477472701'}, 'candidates': []},
                'date': {'selected_value': {'content': '2019-04-12 00:00:00'}, 'candidates': []},
                'due_date': {'selected_value': {'content': '2019-04-19 00:00:00'}, 'candidates': []},
                'email': {'selected_value': {'content': 'test@email.com'}, 'candidates': []},
                'website': {'selected_value': {'content': 'www.test.com'}, 'candidates': []},
                'payment_ref': {'selected_value': {'content': '+++123/1234/12345+++'}, 'candidates': []},
                'iban': {'selected_value': {'content': 'BE01234567890123'}, 'candidates': []},
                'invoice_lines': [
                    {
                        'description': {'selected_value': {'content': 'Test 1'}},
                        'unit_price': {'selected_value': {'content': 100}},
                        'quantity': {'selected_value': {'content': 1}},
                        'taxes': {'selected_values': [{'content': 15, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 100}},
                        'total': {'selected_value': {'content': 115}},
                    },
                    {
                        'description': {'selected_value': {'content': 'Test 2'}},
                        'unit_price': {'selected_value': {'content': 50}},
                        'quantity': {'selected_value': {'content': 2}},
                        'taxes': {'selected_values': [{'content': 0, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 100}},
                        'total': {'selected_value': {'content': 100}},
                    },
                    {
                        'description': {'selected_value': {'content': 'Test 3'}},
                        'unit_price': {'selected_value': {'content': 20}},
                        'quantity': {'selected_value': {'content': 5}},
                        'taxes': {'selected_values': [{'content': 15, 'amount_type': 'percent'}]},
                        'subtotal': {'selected_value': {'content': 100}},
                        'total': {'selected_value': {'content': 115}},
                    },
                ],
            }],
            'status': 'success',
        }

    def _get_email_for_journal_alias(self, attachment=b'My attachment', attach_content_type='application/octet-stream', message_id='some_msg_id'):
        attachment = base64.b64encode(attachment).decode()
        alias = self.journal_with_alias.alias_id
        return textwrap.dedent(f'''\
            MIME-Version: 1.0
            Date: Fri, 26 Nov 2021 16:27:45 +0100
            Message-ID: {message_id}
            Subject: Incoming bill
            From:  Someone <someone@some.company.com>
            To: {alias.display_name}
            Content-Type: multipart/alternative; boundary="000000000000a47519057e029630"

            --000000000000a47519057e029630
            Content-Type: text/plain; charset=\"UTF-8\"


            --000000000000a47519057e029630
            Content-Type: {attach_content_type}
            Content-Transfer-Encoding: base64

            {attachment}

            --000000000000a47519057e029630--
        ''')

    def get_partner_autocomplete_response(self):
        return {
            'company_data': {
                'name': 'Partner',
                'country_code': 'BE',
                'vat': 'BE0477472701',
                'partner_gid': False,
                'city': 'Namur',
                'bank_ids': [],
                'zip': '2110',
                'street': 'OCR street'
            }
        }

    def test_no_merge_check_ocr_status(self):
        # test check_ocr_status without lines merging
        self.env.company.extract_single_line_per_tax = False
        self.env.company.quick_edit_mode = "out_and_in_invoices"  # Fiduciary mode is necessary for out_invoice

        for move_type in ('in_invoice', 'out_invoice'):
            invoice = self.env['account.move'].create({
                'move_type': move_type,
                'extract_state': 'waiting_extraction',
                'extract_document_uuid': 'some_token',
            })

            extract_response = self.get_result_success_response()

            expected_get_results_params = {
                'version': OCR_VERSION,
                'document_token': 'some_token',
                'account_token': invoice._get_iap_account().account_token,
            }

            with self._mock_iap_extract(
                extract_response=extract_response,
                assert_params=expected_get_results_params,
            ):
                invoice._check_ocr_status()

            self.assertEqual(invoice.extract_state, 'waiting_validation')
            self.assertEqual(invoice.extract_status, 'success')
            self.assertEqual(invoice.amount_total, 330)
            self.assertEqual(invoice.amount_untaxed, 300)
            self.assertEqual(invoice.amount_tax, 30)
            self.assertEqual(invoice.invoice_date, fields.Date.from_string('2019-04-12'))
            self.assertEqual(invoice.invoice_date_due, fields.Date.from_string('2019-04-19'))
            self.assertEqual(invoice.payment_reference, "+++123/1234/12345+++")
            if move_type == 'in_invoice':
                self.assertEqual(invoice.ref, 'INV0001')
            else:
                self.assertEqual(invoice.name, 'INV0001')

            self.assertEqual(len(invoice.invoice_line_ids), 3)
            for i, invoice_line in enumerate(invoice.invoice_line_ids):
                self.assertEqual(invoice_line.name, extract_response['results'][0]['invoice_lines'][i]['description']['selected_value']['content'])
                self.assertEqual(invoice_line.price_unit, extract_response['results'][0]['invoice_lines'][i]['unit_price']['selected_value']['content'])
                self.assertEqual(invoice_line.quantity, extract_response['results'][0]['invoice_lines'][i]['quantity']['selected_value']['content'])
                tax = extract_response['results'][0]['invoice_lines'][i]['taxes']['selected_values'][0]
                if tax['content'] == 0:
                    self.assertEqual(len(invoice_line.tax_ids), 0)
                else:
                    self.assertEqual(len(invoice_line.tax_ids), 1)
                    self.assertEqual(invoice_line.tax_ids[0].amount, tax['content'])
                    self.assertEqual(invoice_line.tax_ids[0].amount_type, 'percent')
                self.assertEqual(invoice_line.price_subtotal, extract_response['results'][0]['invoice_lines'][i]['subtotal']['selected_value']['content'])
                self.assertEqual(invoice_line.price_total, extract_response['results'][0]['invoice_lines'][i]['total']['selected_value']['content'])

    def test_included_default_tax(self):
        # test that a tax included coming from the account is not removed from the lines even if it's not detected
        tax_10_included = self.env['account.tax'].create({
            'name': 'Tax 10% included',
            'amount': 10,
            'type_tax_use': 'purchase',
            'price_include': True,
        })
        self.company_data['default_account_expense'].write({
            'tax_ids': tax_10_included
        })

        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['total']['selected_value']['content'] = 300
        for line in extract_response['results'][0]['invoice_lines']:
            line['total'] = line['subtotal']
            line['taxes']['selected_values'] = []

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertEqual(invoice.amount_total, 300)
        for line in invoice.invoice_line_ids:
            self.assertEqual(line.tax_ids[0], tax_10_included)

        # test that the default purchase included tax is the only tax used if it matches the detected tax
        tax_15_included = self.env['account.tax'].create({
            'name': 'Tax 15% included',
            'amount': 15,
            'type_tax_use': 'purchase',
            'price_include': True,
        })
        self.company_data['default_account_expense'].write({
            'tax_ids': tax_15_included
        })

        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice._check_ocr_status()

        self.assertEqual(invoice.amount_total, 330)
        for line in invoice.invoice_line_ids:
            self.assertEqual(line.tax_ids[0], tax_15_included)

    def test_merge_check_ocr_status(self):
        # test check_ocr_status with lines merging
        for move_type in ('in_invoice', 'out_invoice'):
            invoice = self.env['account.move'].create({'move_type': move_type, 'extract_state': 'waiting_extraction'})
            self.env.company.extract_single_line_per_tax = True

            with self._mock_iap_extract(extract_response=self.get_result_success_response()):
                invoice._check_ocr_status()

            self.assertEqual(len(invoice.invoice_line_ids), 2)

            # line 1 and 3 should be merged as they both have a 15% tax
            self.assertEqual(invoice.invoice_line_ids[0].name, "Test - 2019-04-12")
            self.assertEqual(invoice.invoice_line_ids[0].price_unit, 200)
            self.assertEqual(invoice.invoice_line_ids[0].quantity, 1)
            self.assertEqual(len(invoice.invoice_line_ids[0].tax_ids), 1)
            self.assertEqual(invoice.invoice_line_ids[0].tax_ids[0].amount, 15)
            self.assertEqual(invoice.invoice_line_ids[0].tax_ids[0].amount_type, 'percent')
            self.assertEqual(invoice.invoice_line_ids[0].price_subtotal, 200)
            self.assertEqual(invoice.invoice_line_ids[0].price_total, 230)

            # line 2 has no tax
            self.assertEqual(invoice.invoice_line_ids[1].name, "Test - 2019-04-12")
            self.assertEqual(invoice.invoice_line_ids[1].price_unit, 100)
            self.assertEqual(invoice.invoice_line_ids[1].quantity, 1)
            self.assertEqual(len(invoice.invoice_line_ids[1].tax_ids), 0)
            self.assertEqual(invoice.invoice_line_ids[1].price_subtotal, 100)
            self.assertEqual(invoice.invoice_line_ids[1].price_total, 100)

    def test_partner_creation_from_vat(self):
        # test that the partner isn't created if the VAT number isn't valid
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice._check_ocr_status()

        self.assertFalse(invoice.partner_id)

        # test that the partner is created if the VAT number is valid
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(
            extract_response=self.get_result_success_response(),
            partner_autocomplete_response=self.get_partner_autocomplete_response(),
        ):
            invoice._check_ocr_status()

        self.assertEqual(invoice.partner_id.name, 'Partner')
        self.assertEqual(invoice.partner_id.vat, 'BE0477472701')

    def test_partner_selection_from_vat(self):
        # test that if a partner with the VAT found already exists in database it is selected
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        existing_partner = self.env['res.partner'].create({'name': 'Existing partner', 'vat': 'BE0477472701'})

        with self._mock_iap_extract(
            extract_response=self.get_result_success_response(),
            partner_autocomplete_response={'name': 'A new partner', 'vat': 'BE0477472701'},
        ):
            invoice._check_ocr_status()

        self.assertEqual(invoice.partner_id, existing_partner)

    def test_partner_selection_from_iban_and_good_name(self):
        # test that if the IBAN found already exists in database and the name is close enough, it is selected
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        existing_partner = self.env['res.partner'].create({
            'name': 'test',
            'bank_ids': [(0, 0, {'acc_number': "BE01234567890123"})],
        })

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice._check_ocr_status()

        self.assertEqual(invoice.partner_id, existing_partner)

    def test_partner_selection_from_iban_and_bad_name(self):
        # test that if the IBAN found already exists in database but the name is too different, it is not selected
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        self.env['res.partner'].create({
            'name': 'Existing partner',
            'bank_ids': [(0, 0, {'acc_number': "BE01234567890123"})],
        })

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice._check_ocr_status()

        self.assertFalse(invoice.partner_id)

    def test_partner_selection_from_name(self):
        # test that if a partner with a similar name already exists in database it is selected
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        existing_partner = self.env['res.partner'].create({'name': 'Test'})

        self.env['res.partner'].create({'name': 'Partner'})
        self.env['res.partner'].create({'name': 'Another supplier'})

        with self._mock_iap_extract(
            extract_response=self.get_result_success_response(),
            partner_autocomplete_response={'name': 'A new partner', 'vat': 'BE0477472701'}
        ):
            invoice._check_ocr_status()

        self.assertEqual(invoice.partner_id, existing_partner)

        # test that if no partner with a similar name exists, the partner isn't set
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['supplier']['selected_value']['content'] = 'Blablablablabla'

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertFalse(invoice.partner_id)

    def test_multi_currency(self):
        # test that if the multi currency is disabled, the currency isn't changed
        self.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        test_user = self.env.ref('base.user_root')
        test_user.groups_id = [(3, self.env.ref('base.group_multi_currency').id)]

        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        eur_currency = self.env['res.currency'].with_context({'active_test': False}).search([('name', '=', 'EUR')])
        invoice.currency_id = usd_currency.id

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice.with_user(test_user)._check_ocr_status()

        self.assertEqual(invoice.currency_id, usd_currency)

        # test that if multi currency is enabled, the currency is changed
        # group_multi_currency is automatically activated on currency activation
        eur_currency.active = True

        # test with the name of the currency
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        invoice.currency_id = usd_currency.id

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice.with_user(test_user)._check_ocr_status()

        self.assertEqual(invoice.currency_id, eur_currency)

        # test with the symbol of the currency
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        invoice.currency_id = usd_currency.id
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['currency']['selected_value']['content'] = '€'

        with self._mock_iap_extract(extract_response=extract_response):
            invoice.with_user(test_user)._check_ocr_status()

        self.assertEqual(invoice.currency_id, eur_currency)

        # test with the invoice having an invoice line
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        invoice.currency_id = usd_currency.id
        self.env['account.move.line'].create({
            'move_id': invoice.id,
            'account_id': self.company_data['default_account_expense'].id,
            'name': 'Test Invoice Line',
        })

        extract_response = self.get_result_success_response()
        extract_response['results'][0]['currency']['selected_value']['content'] = '€'
        with self._mock_iap_extract(extract_response, {}):
            invoice.with_user(test_user)._check_ocr_status()

        # test if the currency is still the same after extracting the invoice
        self.assertEqual(invoice.currency_id, usd_currency)

    def test_same_name_currency(self):
        # test that when we have several currencies with the same name, and no antecedants with the partner, we take the one that is on our company.
        cad_currency = self.env['res.currency'].with_context({'active_test': False}).search([('name', '=', 'CAD')])
        usd_currency = self.env['res.currency'].with_context({'active_test': False}).search([('name', '=', 'USD')])
        (cad_currency | usd_currency).active = True

        test_user = self.env.user
        test_user.groups_id = [(3, self.env.ref('base.group_multi_currency').id)]
        self.assertEqual(test_user.currency_id, usd_currency)

        extract_response = self.get_result_success_response()
        extract_response['results'][0]['currency']['selected_value']['content'] = 'dollars'

        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        with self._mock_iap_extract(extract_response=extract_response):
            invoice.with_user(test_user)._check_ocr_status()

        self.assertEqual(invoice.currency_id, usd_currency)

        # test that the currency of the last invoice (with a currency) of the partner is used for its next invoice
        partner = self.env['res.partner'].create({'name': 'O Canada'})
        # create an existing invoice with a currency for this partner
        self.env['account.move'].create({'move_type': 'in_invoice', 'partner_id': partner.id, 'currency_id': cad_currency.id})
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'extract_state': 'waiting_extraction',
        })
        with self._mock_iap_extract(extract_response=extract_response):
            invoice.with_user(test_user)._check_ocr_status()

        self.assertEqual(invoice.currency_id, cad_currency)

    def test_tax_adjustments(self):
        # test that if the total computed by Odoo doesn't exactly match the total found by the OCR, the tax are adjusted accordingly
        for move_type in ('in_invoice', 'out_invoice'):
            self.env['res.currency'].search([('name', '!=', 'USD')]).with_context(force_deactivate=True).active = False
            invoice = self.env['account.move'].create({'move_type': move_type, 'extract_state': 'waiting_extraction'})
            extract_response = self.get_result_success_response()
            extract_response['results'][0]['total']['selected_value']['content'] += 0.01

            with self._mock_iap_extract(extract_response=extract_response):
                invoice._check_ocr_status()

            self.assertEqual(invoice.amount_tax, 30.01)
            self.assertEqual(invoice.amount_untaxed, 300)
            self.assertEqual(invoice.amount_total, 330.01)

    def test_non_existing_tax(self):
        # test that if there is an invoice line with a tax which doesn't exist in database it is ignored
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['total']['selected_value']['content'] = 123.4
        extract_response['results'][0]['subtotal']['selected_value']['content'] = 100
        extract_response['results'][0]['invoice_lines'] = [
            {
                'description': {'selected_value': {'content': 'Test 1'}},
                'unit_price': {'selected_value': {'content': 100}},
                'quantity': {'selected_value': {'content': 1}},
                'taxes': {'selected_values': [{'content': 12.34, 'amount_type': 'percent'}]},
                'subtotal': {'selected_value': {'content': 100}},
                'total': {'selected_value': {'content': 123.4}},
            },
        ]

        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 100)
        self.assertEqual(invoice.invoice_line_ids[0].quantity, 1)
        self.assertEqual(len(invoice.invoice_line_ids[0].tax_ids), 0)
        self.assertEqual(invoice.invoice_line_ids[0].price_subtotal, 100)
        self.assertEqual(invoice.invoice_line_ids[0].price_total, 100)

    def test_server_error(self):
        # test that the extract state is set to 'error' if the OCR returned an error
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(extract_response={'status': 'error_internal'}):
            invoice._check_ocr_status()

        self.assertEqual(invoice.extract_state, 'error_status')
        self.assertEqual(invoice.extract_status, 'error_internal')

    def test_server_not_ready(self):
        # test that the extract state is set to 'not_ready' if the OCR didn't finish to process the invoice
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(extract_response=self.parse_processing_response()):
            invoice._check_ocr_status()

        self.assertEqual(invoice.extract_state, 'extract_not_ready')
        self.assertEqual(invoice.extract_status, 'processing')

    def test_preupdate_other_waiting_invoices(self):
        # test that when we update an invoice, other invoices waiting for extraction are updated as well
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        invoice2 = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice.check_ocr_status()

        self.assertEqual(invoice.extract_state, 'waiting_validation')
        self.assertEqual(invoice2.extract_state, 'waiting_validation')

    def test_no_overwrite_client_values(self):
        # test that we are not overwriting the values entered by the client
        partner = self.env['res.partner'].create({'name': 'Blabla', 'vat': 'BE0477472701'})
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'extract_state': 'waiting_extraction',
            'invoice_date': '2019-04-01',
            'date': '2019-04-01',
            'invoice_date_due': '2019-05-01',
            'ref': 'INV1234',
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Blabla',
                'price_unit': 13.0,
                'quantity': 2.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        self.env['res.partner'].create({'name': 'Test', 'vat': 'BE0477472701'})     # this match the partner found in the server response

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice.check_ocr_status()

        self.assertEqual(invoice.extract_state, 'waiting_validation')
        self.assertEqual(invoice.ref, 'INV1234')
        self.assertEqual(invoice.invoice_date, fields.Date.from_string('2019-04-01'))
        self.assertEqual(invoice.invoice_date_due, fields.Date.from_string('2019-05-01'))
        self.assertEqual(invoice.partner_id, partner)

        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids[0].name, "Blabla")
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 13)
        self.assertEqual(invoice.invoice_line_ids[0].quantity, 2)

    def test_invoice_validation(self):
        # test that when we post the invoice, the validation is sent to the server
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'extract_state': 'waiting_extraction',
            'extract_document_uuid': 'some_token',
        })

        with self._mock_iap_extract(
            extract_response=self.get_result_success_response(),
            partner_autocomplete_response=self.get_partner_autocomplete_response(),
        ):
            invoice._check_ocr_status()

        expected_validation_params = {
            'version': OCR_VERSION,
            'values': {
                'total': {'content': invoice.amount_total},
                'subtotal': {'content': invoice.amount_untaxed},
                'total_tax_amount': {'content': invoice.amount_tax},
                'date': {'content': str(invoice.invoice_date)},
                'due_date': {'content': str(invoice.invoice_date_due)},
                'invoice_id': {'content': invoice.ref},
                'partner': {'content': invoice.partner_id.name},
                'VAT_Number': {'content': invoice.partner_id.vat},
                'currency': {'content': invoice.currency_id.name},
                'payment_ref': {'content': invoice.payment_reference},
                'iban': {'content': invoice.partner_bank_id.acc_number},
                'SWIFT_code': {'content': invoice.partner_bank_id.bank_bic},
                'merged_lines': True,
                'invoice_lines': {
                    'lines': [
                        {
                            'description': il.name,
                            'quantity': il.quantity,
                            'unit_price': il.price_unit,
                            'product': il.product_id.id,
                            'taxes_amount': round(il.price_total - il.price_subtotal, 2),
                            'taxes': [
                                {
                                    'amount': tax.amount,
                                    'type': tax.amount_type,
                                    'price_include': tax.price_include
                                } for tax in il.tax_ids
                            ],
                            'subtotal': il.price_subtotal,
                            'total': il.price_total,
                        } for il in invoice.invoice_line_ids
                    ]
                }
            },
            'document_token': 'some_token',
            'account_token': invoice._get_iap_account().account_token,
        }

        with self._mock_iap_extract(
            extract_response=self.validate_success_response(),
            assert_params=expected_validation_params,
        ):
            invoice.action_post()

        self.assertEqual(invoice.extract_state, 'done')
        self.assertEqual(invoice._get_validation('total')['content'], invoice.amount_total)
        self.assertEqual(invoice._get_validation('subtotal')['content'], invoice.amount_untaxed)
        self.assertEqual(invoice._get_validation('date')['content'], str(invoice.invoice_date))
        self.assertEqual(invoice._get_validation('due_date')['content'], str(invoice.invoice_date_due))
        self.assertEqual(invoice._get_validation('invoice_id')['content'], invoice.ref)
        self.assertEqual(invoice._get_validation('partner')['content'], invoice.partner_id.name)
        self.assertEqual(invoice._get_validation('total_tax_amount')['content'], invoice.amount_tax)
        self.assertEqual(invoice._get_validation('VAT_Number')['content'], invoice.partner_id.vat)
        self.assertEqual(invoice._get_validation('currency')['content'], invoice.currency_id.name)
        self.assertEqual(invoice._get_validation('payment_ref')['content'], invoice.payment_reference)
        validation_invoice_lines = invoice._get_validation('invoice_lines')['lines']
        for i, il in enumerate(invoice.invoice_line_ids):
            self.assertDictEqual(validation_invoice_lines[i], {
                'description': il.name,
                'quantity': il.quantity,
                'unit_price': il.price_unit,
                'product': il.product_id.id,
                'taxes_amount': round(il.price_total - il.price_subtotal, 2),
                'taxes': [{
                    'amount': tax.amount,
                    'type': tax.amount_type,
                    'price_include': tax.price_include} for tax in il.tax_ids],
                'subtotal': il.price_subtotal,
                'total': il.price_total,
            })

    def test_automatic_sending_vendor_bill_message_post(self):
        # test that a vendor bill is automatically sent to the OCR server when a message with attachment is posted and the option is enabled
        self.env.company.extract_in_invoice_digitalization_mode = 'auto_send'
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'no_extract_requested'})
        test_attachment = self.env['ir.attachment'].create({
            'name': "an attachment",
            'datas': base64.b64encode(b'My attachment'),
        })

        expected_parse_params = {
            'version': OCR_VERSION,
            'account_token': 'test_token',
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'documents': [test_attachment.datas.decode('utf-8')],
            'user_infos': {
                'perspective': 'client',
                'user_company_VAT': invoice.company_id.vat,
                'user_company_country_code': invoice.company_id.country_id.code,
                'user_company_name': invoice.company_id.name,
                'user_email': self.user.email,
                'user_lang': self.env.ref('base.user_root').lang,
            },
            'webhook_url': f'{invoice.get_base_url()}/account_invoice_extract/request_done',
        }

        if self.env['ir.module.module']._get('account_invoice_extract_purchase').state == 'installed':
            expected_parse_params['user_infos']['purchase_order_regex'] = r'P\d{5}'

        with self._mock_iap_extract(
            extract_response=self.parse_success_response(),
            assert_params=expected_parse_params,
        ):
            invoice.message_post(attachment_ids=[test_attachment.id])

        self.assertEqual(invoice.extract_state, 'waiting_extraction')
        self.assertEqual(invoice.extract_document_uuid, 'some_token')

    def test_automatic_sending_vendor_bill_main_attachment(self):
        # test that a vendor bill is automatically sent to the OCR server when a main attachment is registered and the option is enabled
        self.env.company.extract_in_invoice_digitalization_mode = 'auto_send'
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'no_extract_requested'})
        test_attachment = self.env['ir.attachment'].create({
            'name': "an attachment",
            'datas': base64.b64encode(b'My attachment'),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            test_attachment.register_as_main_attachment()

        self.assertEqual(invoice.extract_state, 'waiting_extraction')
        self.assertEqual(invoice.extract_document_uuid, 'some_token')

    def test_automatic_sending_multiple_vendor_bill_message_post(self):
        # test that when multiple pdf attachments are posted and the option is enabled each one is split
        # into a separate move
        self.env.company.extract_in_invoice_digitalization_mode = 'auto_send'
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'no_extract_requested'})
        with file_open('base/tests/minimal.pdf', 'rb') as file:
            pdf_bytes = file.read()
        test_attachments = self.env['ir.attachment'].create([{
            'name': 'Attachment 1',
            'datas': base64.b64encode(pdf_bytes),
            'mimetype': 'application/pdf',
        }, {
            'name': 'Attachment 2',
            'datas': base64.b64encode(pdf_bytes),
            'mimetype': 'application/pdf',
        }])

        with self._mock_iap_extract(
            extract_response=self.parse_success_response(),
        ):
            invoice.with_context(from_alias=True, default_move_type='in_invoice', default_journal_id=invoice.journal_id.id).message_post(attachment_ids=test_attachments.ids)

        new_invoice_id = invoice.id + 1
        invoices = invoice
        invoices |= self.env['account.move'].search([('id', '=', new_invoice_id)])

        self.assertEqual(len(invoices), 2, "Two separate bills should have been created")
        for inv, att in zip(invoices, test_attachments):
            self.assertEqual(inv.extract_state, 'waiting_extraction')
            self.assertEqual(inv.extract_document_uuid, 'some_token')
            self.assertEqual(inv.message_main_attachment_id, att)

    def test_automatic_sending_customer_invoice_upload(self):
        # test that a customer invoice is automatically sent to the OCR server when uploaded and the option is enabled
        self.env.company.extract_out_invoice_digitalization_mode = 'auto_send'
        test_attachment = self.env['ir.attachment'].create({
            'name': "an attachment",
            'datas': base64.b64encode(b'My attachment'),
        })
        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            action = self.env['account.journal'].with_context(default_move_type='out_invoice').create_document_from_attachment(test_attachment.id)

        invoice = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(invoice.extract_state, 'waiting_extraction')
        self.assertEqual(invoice.extract_document_uuid, 'some_token')

    def test_automatic_sending_customer_invoice_email_alias(self):
        # test that a customer invoice is automatically sent to the OCR server when sent via email alias and the option is enabled
        self.env.company.extract_out_invoice_digitalization_mode = 'auto_send'
        with file_open('base/tests/minimal.pdf', 'rb') as file:
            pdf_bytes = file.read()
        mail = self._get_email_for_journal_alias(
            attachment=pdf_bytes,
            attach_content_type='application/pdf',
            message_id='message_2'
        )
        with self._mock_iap_extract(self.parse_success_response()):
            invoice = self.env['account.move'].browse(self.env['mail.thread'].message_process('account.move', mail))
        self.assertEqual(invoice.extract_state, 'waiting_extraction')
        self.assertEqual(invoice.extract_document_uuid, 'some_token')

    def test_no_automatic_sending_customer_invoice_email_alias(self):
        # test that a customer invoice isn't automatically sent to the OCR server when sent via email alias and the option is disabled
        self.env.company.extract_out_invoice_digitalization_mode = 'manual_send'
        mail = self._get_email_for_journal_alias()
        with self._mock_iap_extract(self.parse_success_response()):
            invoice = self.env['account.move'].browse(self.env['mail.thread'].message_process('account.move', mail))
        self.assertEqual(invoice.extract_state, 'no_extract_requested')

    def test_automatic_sending_customer_invoice_email_alias_pdf_filter(self):
        # test that alias_auto_extract_pdfs_only option successfully prevent non pdf attachments to be sent to OCR
        self.env.company.extract_out_invoice_digitalization_mode = 'auto_send'
        self.journal_with_alias.alias_auto_extract_pdfs_only = True

        # attachment is not pdf -> do not extract
        mail = self._get_email_for_journal_alias(message_id='message_1')
        with self._mock_iap_extract(self.parse_success_response()):
            invoice = self.env['account.move'].browse(self.env['mail.thread'].message_process('account.move', mail))
        self.assertEqual(invoice.extract_state, 'no_extract_requested')
        self.assertFalse(invoice.extract_document_uuid)

        # attachment is pdf -> extract
        with file_open('base/tests/minimal.pdf', 'rb') as file:
            pdf_bytes = file.read()
        mail = self._get_email_for_journal_alias(
            attachment=pdf_bytes,
            attach_content_type='application/pdf',
            message_id='message_2'
        )
        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            invoice = self.env['account.move'].browse(self.env['mail.thread'].message_process('account.move', mail))
        self.assertEqual(invoice.extract_state, 'waiting_extraction')
        self.assertEqual(invoice.extract_document_uuid, 'some_token')

    def test_no_automatic_sending_customer_invoice_message_post(self):
        # test that a customer invoice isn't automatically sent to the OCR server when a message with attachment is posted and the option is enabled
        self.env.company.extract_out_invoice_digitalization_mode = 'auto_send'
        invoice = self.env['account.move'].create({'move_type': 'out_invoice', 'extract_state': 'no_extract_requested'})
        test_attachment = self.env['ir.attachment'].create({
            'name': "an attachment",
            'datas': base64.b64encode(b'My attachment'),
        })

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            invoice.message_post(attachment_ids=[test_attachment.id])

        self.assertEqual(invoice.extract_state, 'no_extract_requested')
        self.assertFalse(invoice.extract_document_uuid)

    def test_no_automatic_sending_customer_invoice_main_attachment(self):
        # test that a customer invoice isn't automatically sent to the OCR server when a main attachment is registered and the option is enabled
        self.env.company.extract_out_invoice_digitalization_mode = 'auto_send'
        invoice = self.env['account.move'].create({'move_type': 'out_invoice', 'extract_state': 'no_extract_requested'})
        test_attachment = self.env['ir.attachment'].create({
            'name': "an attachment",
            'datas': base64.b64encode(b'My attachment'),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            test_attachment.register_as_main_attachment()

        self.assertEqual(invoice.extract_state, 'no_extract_requested')
        self.assertFalse(invoice.extract_document_uuid)

    def test_no_automatic_sending_option_disabled(self):
        # test that an invoice isn't automatically sent to the OCR server when the option is disabled
        self.env.company.extract_in_invoice_digitalization_mode = 'manual_send'
        self.env.company.extract_out_invoice_digitalization_mode = 'manual_send'
        for move_type in ('in_invoice', 'out_invoice'):
            # test with message_post()
            invoice = self.env['account.move'].create({'move_type': move_type, 'extract_state': 'no_extract_requested'})
            test_attachment = self.env['ir.attachment'].create({
                'name': "an attachment",
                'datas': base64.b64encode(b'My attachment'),
            })

            with self._mock_iap_extract(extract_response=self.parse_success_response()):
                invoice.message_post(attachment_ids=[test_attachment.id])

            self.assertEqual(invoice.extract_state, 'no_extract_requested')

            # test with register_as_main_attachment()
            invoice = self.env['account.move'].create({'move_type': move_type, 'extract_state': 'no_extract_requested'})
            test_attachment = self.env['ir.attachment'].create({
                'name': "another attachment",
                'datas': base64.b64encode(b'My other attachment'),
                'res_model': 'account.move',
                'res_id': invoice.id,
            })

            with self._mock_iap_extract(extract_response=self.parse_success_response()):
                test_attachment.register_as_main_attachment()

            self.assertEqual(invoice.extract_state, 'no_extract_requested')
            self.assertFalse(invoice.extract_document_uuid)

    def test_bank_account(self):
        # test that the bank account is set when an iban is found

        # test that an account is created if no existing matches the account number
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(
            extract_response=self.get_result_success_response(),
            partner_autocomplete_response=self.get_partner_autocomplete_response(),
        ):
            invoice._check_ocr_status()

        self.assertEqual(invoice.partner_bank_id.acc_number, 'BE01234567890123')

        # test that it uses the existing bank account if it exists
        created_bank_account = invoice.partner_bank_id
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            invoice._check_ocr_status()

        self.assertEqual(invoice.partner_bank_id, created_bank_account)

    def test_tax_price_included(self):
        self.env['account.tax'].create({
            'name': 'Tax 12% included',
            'amount': 12,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
            'company_id': self.company_data['company'].id
        })

        invoice = self._create_invoice_with_tax()

        self.assertRecordValues(invoice.invoice_line_ids, [{
                'price_unit': 112,
                'quantity': 1,
                'price_subtotal': 100,
                'price_total': 112,
        }])

    def test_tax_price_excluded(self):
        self.env['account.tax'].create({
            'name': 'Tax 12% excluded',
            'amount': 12,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'company_id': self.company_data['company'].id
        })

        invoice = self._create_invoice_with_tax()

        self.assertRecordValues(invoice.invoice_line_ids, [{
                'price_unit': 100,
                'quantity': 1,
                'price_subtotal': 100,
                'price_total': 112,
        }])

    def _create_invoice_with_tax(self):
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})
        extract_response = self.get_result_success_response()
        extract_response['results'][0]['total']['selected_value']['content'] = 112
        extract_response['results'][0]['subtotal']['selected_value']['content'] = 100
        extract_response['results'][0]['invoice_lines'] = [
            {
                'description': {'selected_value': {'content': 'Test 1'}},
                'unit_price': {'selected_value': {'content': 100}},
                'quantity': {'selected_value': {'content': 1}},
                'taxes': {'selected_values': [{'content': 12, 'amount_type': 'percent'}]},
                'subtotal': {'selected_value': {'content': 100}},
                'total': {'selected_value': {'content': 112}},
            },
        ]

        with self._mock_iap_extract(extract_response, {}):
            invoice._check_ocr_status()

        return invoice

    def test_credit_note_detection(self):
        # test that move type changes, if and only if the type in the ocr results is refund the current move type is invoice
        invoice = self.env['account.move'].create({'move_type': 'in_invoice', 'extract_state': 'waiting_extraction'})

        extract_response = self.get_result_success_response()
        extract_response['results'][0]['type'] = 'refund'
        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertEqual(invoice.move_type, 'in_refund')

        invoice = self.env['account.move'].create({'move_type': 'out_refund', 'extract_state': 'waiting_extraction'})

        extract_response['results'][0]['type'] = 'invoice'
        with self._mock_iap_extract(extract_response=extract_response):
            invoice._check_ocr_status()

        self.assertEqual(invoice.move_type, 'out_refund')

    def test_action_reload_ai_data(self):
        # test that the "Reload AI data" button overwrites the content of the invoice with the OCR results
        self.env.company.extract_single_line_per_tax = False
        ocr_partner = self.env['res.partner'].create({'name': 'Test', 'vat': 'BE0477472701'})

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'extract_state': 'waiting_validation',
            'invoice_date': '2019-04-01',
            'date': '2019-04-01',
            'invoice_date_due': '2019-05-01',
            'ref': 'INV1234',
            'payment_reference': '+++111/2222/33333+++',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Blabla',
                'price_unit': 13.0,
                'quantity': 2.0,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })

        extract_response = self.get_result_success_response()
        with self._mock_iap_extract(extract_response=extract_response):
            invoice.action_reload_ai_data()

        self.assertEqual(invoice.extract_state, 'waiting_validation')

        # Check that the fields have been overwritten with the OCR results
        self.assertEqual(invoice.amount_total, 330)
        self.assertEqual(invoice.amount_untaxed, 300)
        self.assertEqual(invoice.amount_tax, 30)
        self.assertEqual(invoice.partner_id, ocr_partner)
        self.assertEqual(invoice.invoice_date, fields.Date.from_string('2019-04-12'))
        self.assertEqual(invoice.invoice_date_due, fields.Date.from_string('2019-04-19'))
        self.assertEqual(invoice.payment_reference, '+++123/1234/12345+++')
        self.assertEqual(invoice.ref, 'INV0001')
        self.assertEqual(invoice.invoice_line_ids.mapped('name'), ["Test 1", "Test 2", "Test 3"])
