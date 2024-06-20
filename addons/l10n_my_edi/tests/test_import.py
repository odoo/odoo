# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from unittest.mock import patch

import dateutil
from freezegun import freeze_time

from odoo import tools, Command
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

CONTACT_PROXY_METHOD = 'odoo.addons.l10n_my_edi.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_my_edi_contact_proxy'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestXMLImport(TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='my'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        with file_open('l10n_my_edi/tests/files/invoice.xml', "r") as file:
            cls.xml_file_data = file.read()
        with file_open('l10n_my_edi/tests/files/invoice.json', "r") as file:
            cls.json_file_data = file.read()
        with file_open('l10n_my_edi/tests/files/credit_note.xml', "r") as file:
            cls.credit_note_file_data = file.read()

        # TIN number is required
        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_edi_industrial_classification': cls.env['l10n_my_edi.industry_classification'].search(
                [('code', '=', '01111')]).id,
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'phone': '+60123456789',
        })
        cls.partner_a.write({
            'vat': 'C2584563201',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234568',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'phone': '+60123456786',
        })

        # For simplicity, we will test everything using a 'test' mode user, but we create it using demo to avoid triggering anything.
        cls.proxy_user = cls.env['account_edi_proxy_client.user']._register_proxy_user(cls.company_data['company'], 'l10n_my_edi', 'demo')
        cls.proxy_user.edi_mode = 'test'

        # One 10% tax, one 6% Exempt
        cls.env['account.tax'].create({
            'name': '10% P',
            'amount': 10.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
        })
        cls.env['account.tax'].create({
            'name': '6% P',
            'amount': 6.0,
            'l10n_my_tax_type': 'E',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 0,
                    'repartition_type': 'tax',
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 0,
                    'repartition_type': 'tax',
                }),
            ],
        })

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_01_import_xml(self):
        """ Import the sample xml file from the sdk.
        Only a single test is done, as we're reusing most of the UBL 2.1 logic which is already tested.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_01_mock):
            # This method would be used by the cron to import files.
            invoice = self.env['account.move']._l10n_my_edi_import_from_myinvois('123458974513518', '01', 'valid', '1236547985', self.company_data['company'])

        # We imported the invoice, we now check the new invoice values to ensure that it has the necessary data.
        self.assertRecordValues(
            invoice,
            [{
                'l10n_my_edi_custom_form_reference': '1356487',
                'invoice_incoterm_id': self.env.ref('account.incoterm_CPT').id,
                'l10n_my_edi_state': 'valid',
                'l10n_my_edi_validation_time': dateutil.parser.isoparse('2024-07-15T10:00:00Z').replace(tzinfo=None),
                'l10n_my_edi_submission_uid': '1236547985',
                'l10n_my_edi_external_uuid': '123458974513518',
            }]
        )
        # Also check that the imported partner has their malaysian info filled
        self.assertRecordValues(
            invoice.partner_id,
            [{
                'name': 'My Test Company',
                'vat': 'C58621197045',
                'country_code': 'MY',
                'sst_registration_number': 'A01-2345-67891012',
                'ttx_registration_number': '123-4567-89012345',
                'l10n_my_identification_type': 'BRN',
                'l10n_my_identification_number': '202001234567',
            }]
        )
        # Finally we do a quick amount check.
        self.assertEqual(tools.float_compare(invoice.amount_untaxed, 147, 2), 0)
        self.assertEqual(tools.float_compare(invoice.amount_tax, 14.7, 2), 0)
        self.assertEqual(tools.float_compare(invoice.amount_total, 161.7, 2), 0)

    def test_02_import_json(self):
        """ When receiving a JSON, we transform it in XML and then import using the same code as XML files. """
        with patch(CONTACT_PROXY_METHOD, new=self._test_02_mock):
            # This method would be used by the cron to import files.
            invoice = self.env['account.move']._l10n_my_edi_import_from_myinvois('123458974513518', '01', 'valid', '1236547985', self.company_data['company'])

        # We imported the invoice, we now check the new invoice values to ensure that it has the necessary data.
        self.assertRecordValues(
            invoice,
            [{
                'l10n_my_edi_custom_form_reference': '1356487',
                'invoice_incoterm_id': self.env.ref('account.incoterm_CPT').id,
                'l10n_my_edi_state': 'valid',
                'l10n_my_edi_validation_time': dateutil.parser.isoparse('2024-07-15T10:00:00Z').replace(tzinfo=None),
                'l10n_my_edi_submission_uid': '1236547985',
                'l10n_my_edi_external_uuid': '123458974513518',
            }]
        )
        # Also check that the imported partner has their malaysian info filled
        self.assertRecordValues(
            invoice.partner_id,
            [{
                'name': 'My Test Company',
                'vat': 'C58621197045',
                'country_code': 'MY',
                'sst_registration_number': 'A01-2345-67891012',
                'ttx_registration_number': '123-4567-89012345',
                'l10n_my_identification_type': 'BRN',
                'l10n_my_identification_number': '202001234567',
            }]
        )
        # Finally we do a quick amount check.
        self.assertEqual(tools.float_compare(invoice.amount_untaxed, 147, 2), 0)
        self.assertEqual(tools.float_compare(invoice.amount_tax, 14.7, 2), 0)
        self.assertEqual(tools.float_compare(invoice.amount_total, 161.7, 2), 0)

    def test_03_import_credit_note(self):
        """ Test importing simple credit note """
        with patch(CONTACT_PROXY_METHOD, new=self._test_03_mock):
            # We first get the invoice.
            invoice = self.env['account.move']._l10n_my_edi_import_from_myinvois('123458974513518', '01', 'valid', '1236547985', self.company_data['company'])
            # Then get the credit note.
            credit_note = self.env['account.move']._l10n_my_edi_import_from_myinvois('123458974513519', '02', 'valid', '1236547985', self.company_data['company'])

        # We imported the invoice, we now check the new invoice values to ensure that it has the necessary data.
        self.assertRecordValues(
            credit_note,
            [{
                'l10n_my_edi_custom_form_reference': '1356487',
                'l10n_my_edi_state': 'valid',
                'l10n_my_edi_validation_time': dateutil.parser.isoparse('2024-07-15T10:00:00Z').replace(tzinfo=None),
                'l10n_my_edi_submission_uid': '1236547985',
                'l10n_my_edi_external_uuid': '123458974513519',
                'reversed_entry_id': invoice.id,
            }]
        )
        # Also check that the imported partner has their malaysian info filled
        self.assertRecordValues(
            credit_note.partner_id,
            [{
                'name': 'My Test Company',
                'vat': 'C58621197045',
                'country_code': 'MY',
                'sst_registration_number': 'A01-2345-67891012',
                'ttx_registration_number': '123-4567-89012345',
                'l10n_my_identification_type': 'BRN',
                'l10n_my_identification_number': '202001234567',
            }]
        )
        # Finally we do a quick amount check.
        self.assertEqual(tools.float_compare(invoice.amount_untaxed, 147, 2), 0)
        self.assertEqual(tools.float_compare(invoice.amount_tax, 14.7, 2), 0)
        self.assertEqual(tools.float_compare(invoice.amount_total, 161.7, 2), 0)

    def test_04_import_cron(self):
        """ Import multiple documents using the cron. Then run it again to update the statuses. """
        with patch(CONTACT_PROXY_METHOD, new=self._test_04_mock):
            self.invoiced_received = False
            self.env['account.move']._cron_l10n_my_edi_synchronize_myinvois()
            moves = self.env['account.move'].search([
                ('company_id', '=', self.company_data['company'].id),
                ('move_type', 'in', self.env['account.move'].get_purchase_types(False))
            ])
            self.assertEqual(len(moves), 3)  # invoice, invoice, credit note

            self.invoiced_received = True

            self.env['account.move']._cron_l10n_my_edi_synchronize_myinvois()
            moves = self.env['account.move'].search([
                ('company_id', '=', self.company_data['company'].id),
                ('move_type', 'in', self.env['account.move'].get_purchase_types(False))
            ])
            self.assertEqual(len(moves), 3)  # We should not have re-imported the same invoices. But their satus is updated.
            self.assertListEqual(moves.mapped('l10n_my_edi_state'), ['valid', 'valid', 'valid'])

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------

    def _test_01_mock(self, endpoint, params):
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_document_file':
            return {
                'document': self.xml_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_02_mock(self, endpoint, params):
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_document_file':
            return {
                'document': self.json_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_03_mock(self, endpoint, params):
        if endpoint == 'api/l10n_my_edi/1/get_document_file' and params['document_uuid'] == '123458974513518':
            return {
                'document': self.xml_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        elif endpoint == 'api/l10n_my_edi/1/get_document_file' and params['document_uuid'] == '123458974513519':
            return {
                'document': self.credit_note_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_04_mock(self, endpoint, params):
        if endpoint == 'api/l10n_my_edi/1/search_invoices':
            return {
                'sent_invoices': {},
                'received_invoices': {
                    '123458974513518': {
                        'uuid': '123458974513518',
                        'submission_uid': '123',
                        'status': 'in_progress' if not self.invoiced_received else 'valid',
                        'type_name': '01',
                    },
                    '123458974513519': {
                        'uuid': '123458974513519',
                        'submission_uid': '456',
                        'status': 'in_progress' if not self.invoiced_received else 'valid',
                        'type_name': '01',
                    },
                    '123458974513520': {
                        'uuid': '123458974513520',
                        'submission_uid': '789',
                        'status': 'in_progress' if not self.invoiced_received else 'valid',
                        'type_name': '02',
                    },
                },
            }
        elif endpoint == 'api/l10n_my_edi/1/get_document_file' and params['document_uuid'] == '123458974513518':
            return {
                'document': self.xml_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        elif endpoint == 'api/l10n_my_edi/1/get_document_file' and params['document_uuid'] == '123458974513519':
            return {
                'document': self.json_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        elif endpoint == 'api/l10n_my_edi/1/get_document_file' and params['document_uuid'] == '123458974513520':
            return {
                'document': self.credit_note_file_data,
                'validation_time': '2024-07-15T10:00:00Z',
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
