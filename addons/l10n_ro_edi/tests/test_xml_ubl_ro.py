import datetime
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import (
    TestUBLCommon,
)
from odoo.addons.l10n_ro_edi.models.account_move import HOLDING_DAYS


def _patch_request_ciusro_download_answer(company, key_download, session):
    answer_data = {
        '3029027561': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_1',
                'key_certificate': 'KEY_CERT_1',
            },
            'invoice': {
                'name': 'INV/2017/00001',
            },
        },
        '3029027562': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_2',
                'key_certificate': 'KEY_CERT_2',
            },
            'invoice': {
                'name': 'INV/2017/00002',
            },
        },
        '3030159318': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_3',
                'key_certificate': 'KEY_CERT_3',
            },
            'invoice': {
                'error': 'There has been an error',
            },
        },
        '3030439533': {
            'signature': {
                'attachment_raw': b'Y291Y291',
                'key_signature': 'KEY_SIG_4',
                'key_certificate': 'KEY_CERT_4',
            },
            'invoice': {
                'name': 'INV/2025/00006',
                'amount_total': '1785.0',
                'seller_vat': '8001011234567',
                'date': datetime.date(2017, 1, 1),
                'attachment_raw': file_open("l10n_ro_edi/tests/test_files/from_odoo/ciusro_in_invoice.xml").read(),
            },
        },
    }
    return answer_data.get(key_download, {})


def _patch_request_ciusro_synchronize_invoices(company, session, nb_days=1):
    sent_invoices_accepted_messages = [
        {
            'data_creare': '202503271639',
            'cif': company.vat,
            'id_solicitare': '5019882651',
            'detalii': f"Factura cu id_incarcare=5019882651 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA TRIMISA',
            'id': '3029027561',
            'answer': _patch_request_ciusro_download_answer(company, '3029027561', None),
        },
        {
            'data_creare': '202503271639',
            'cif': company.vat,
            'id_solicitare': '5019882652',
            'detalii': f"Factura cu id_incarcare=5019882652 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA TRIMISA',
            'id': '3029027562',
            'answer': _patch_request_ciusro_download_answer(company, '3029027562', None),
        },
        {
            'data_creare': '202503271639',
            'cif': company.vat,
            'id_solicitare': '5019882653',
            'detalii': f"Factura cu id_incarcare=5019882653 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA TRIMISA',
            'id': '3029027562',
            'answer': _patch_request_ciusro_download_answer(company, '3029027562', None),
        },
    ]
    sent_invoices_refused_messages = [
        {
            'data_creare': '202504081504',
            'cif': company.vat,
            'id_solicitare': '5020592384',
            'detalii': 'Erori de validare identificate la factura transmisa cu id_incarcare=5020592384',
            'tip': 'ERORI FACTURA',
            'id': '3030159318',
            'answer': _patch_request_ciusro_download_answer(company, '3030159318', None),
        },
    ]
    received_bills_messages = [
        {
            'data_creare': '202504011105',
            'cif': company.vat,
            'id_solicitare': '5020704741',
            'detalii': f"Factura cu id_incarcare=5020704741 emisa de cif_emitent={company.vat} pentru cif_beneficiar=RO1234567897",
            'tip': 'FACTURA PRIMITA',
            'id': '3030439533',
            'answer': _patch_request_ciusro_download_answer(company, '3030439533', None),
        }
    ]
    return {
        'sent_invoices_accepted_messages': sent_invoices_accepted_messages,
        'sent_invoices_refused_messages': sent_invoices_refused_messages,
        'received_bills_messages': received_bills_messages,
    }


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLRO(TestUBLCommon):

    @classmethod
    @TestUBLCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.ro').id,  # needed to compute peppol_endpoint based on VAT
            'state_id': cls.env.ref('base.RO_B').id,
            'name': 'Hudson Construction',
            'city': 'SECTOR1',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'street': "Strada Kunst, 3",
        })

        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RO98RNCB1234567890123456',
        })

        cls.partner_a = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.ro').id,
            'state_id': cls.env.ref('base.RO_B').id,
            'name': 'Roasted Romanian Roller',
            'city': 'SECTOR3',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 780',
            'street': "Rolling Roast, 88",
            'bank_ids': [(0, 0, {'acc_number': 'RO98RNCB1234567890123456'})],
            'ref': 'ref_partner_a',
            'invoice_edi_format': 'ciusro',
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.ro').id,
        })

    ####################################################
    # Test export - import
    ####################################################

    def create_move(self, move_type, send=True, **kwargs):
        return self._generate_move(
            self.env.company.partner_id,
            self.partner_a,
            send=send,
            move_type=move_type,
            invoice_line_ids=[
                {
                    'name': 'Test Product A',
                    'product_id': self.product_a.id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'name': 'Test Product B',
                    'product_id': self.product_b.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
            ],
            **kwargs
        )

    def get_attachment(self, move):
        self.assertTrue(move.ubl_cii_xml_id)
        self.assertEqual(move.ubl_cii_xml_id.name[-11:], "cius_ro.xml")
        return move.ubl_cii_xml_id

    ####################################################
    # Testing of the XML generation
    ####################################################

    def test_export_invoice(self):
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice.xml')

    def test_export_credit_note(self):
        refund = self.create_move("out_refund", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(refund)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_refund.xml')

    def test_export_credit_note_with_negative_quantity(self):
        refund = self._generate_move(
            self.env.company.partner_id,
            self.partner_a,
            send=True,
            move_type="out_refund",
            currency_id=self.company.currency_id.id,
            invoice_line_ids=[
                {
                    'name': 'Test Product A',
                    'product_id': self.product_a.id,
                    'quantity': -1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'name': 'Test Product B',
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'price_unit': 0.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'name': 'Test Downpayment',
                    'product_id': False,
                    'quantity': 1.0,
                    'price_unit': 600.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                }
            ]
        )
        attachment = self.get_attachment(refund)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_refund_negative_quantity.xml')

    def test_export_invoice_different_currency(self):
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_different_currency.xml')

    def test_export_invoice_without_country_code_prefix_in_vat(self):
        self.company_data['company'].write({'vat': '1234567897'})
        self.partner_a.write({'vat': False})
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_no_prefix_vat.xml')

    def test_export_no_vat_but_have_company_registry(self):
        self.company_data['company'].write({'vat': False, 'company_registry': 'RO1234567897'})
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice.xml')

    def test_export_no_vat_but_have_company_registry_without_prefix(self):
        self.company_data['company'].write({'vat': False, 'company_registry': '1234567897'})
        self.partner_a.write({'vat': False})
        invoice = self.create_move("out_invoice", currency_id=self.company.currency_id.id)
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_no_prefix_company_registry.xml')

    def test_export_no_vat_and_no_company_registry_raises_error(self):
        self.company_data['company'].write({'vat': False, 'company_registry': False})
        invoice = self.create_move("out_invoice", send=False)
        with self.assertRaisesRegex(UserError, "doesn't have a VAT nor Company ID"):
            invoice._generate_and_send(allow_fallback_pdf=False, template_id=self.move_template.id)

    def test_export_constraints(self):
        self.company_data['company'].company_registry = False
        for required_field in ('city', 'street', 'state_id', 'vat'):
            prev_val = self.company_data["company"][required_field]
            self.company_data["company"][required_field] = False
            invoice = self.create_move("out_invoice", send=False)
            with self.assertRaisesRegex(UserError, "required"):
                invoice._generate_and_send(allow_fallback_pdf=False, template_id=self.move_template.id)
            self.company_data["company"][required_field] = prev_val

        self.company_data["company"].city = "Bucharest"
        invoice = self.create_move("out_invoice", send=False)
        with self.assertRaisesRegex(UserError, "city name must be 'SECTORX'"):
            invoice._generate_and_send(allow_fallback_pdf=False, template_id=self.move_template.id)

    ####################################################
    # Testing of the bill synchronization with SPV
    ####################################################

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_bill_found(self):
        """ Tests that if a bill with the same index is found, do nothing.
        """
        bill = self.create_move('in_invoice', send=False, l10n_ro_edi_index='5020704741', l10n_ro_edi_state='invoice_validated')

        document_count = len(bill.l10n_ro_edi_document_ids)
        message_count = len(bill.message_ids)

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(len(bill.l10n_ro_edi_document_ids), document_count)
        self.assertEqual(len(bill.message_ids), message_count)

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_bill_update_index(self):
        """ Tests that if a bill with the same partner VAT, amount match and date is found,
            we update the index and validate the invoice.
        """
        # Need a bill without index and for which the partner VAT and amount match the data returned
        bill = self.create_move('in_invoice', send=False)
        self.partner_a.vat = '8001011234567'

        self.assertEqual(bill.l10n_ro_edi_index, False)
        self.assertEqual(bill.l10n_ro_edi_state, False)

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(bill.l10n_ro_edi_index, '5020704741')
        self.assertEqual(bill.l10n_ro_edi_state, 'invoice_validated')

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_bill_creation(self):
        """ Tests that if no similar bills are found, we create one and fill it up with the XML content.
        """
        bills = self.env['account.move'].search([
            ('move_type', 'in', self.env['account.move'].get_purchase_types()),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertEqual(len(bills), 0)

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        bills = self.env['account.move'].search([
            ('move_type', 'in', self.env['account.move'].get_purchase_types()),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertEqual(len(bills), 1)
        self.assertEqual(bills.state, 'draft')
        self.assertEqual(bills.amount_total, 1785.0)
        self.assertEqual(bills.commercial_partner_id.vat, '8001011234567')
        self.assertEqual(bills.l10n_ro_edi_index, '5020704741')
        self.assertEqual(bills.l10n_ro_edi_state, 'invoice_validated')

    ####################################################
    # Testing of the invoice synchronization with SPV
    ####################################################

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_validation(self):
        ''' Test that a sent invoice status is validated.
        '''
        # Create an invoice that will match the success response returned by the server
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='5019882651', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_validated')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_validation_without_index(self):
        ''' Test that a sent invoice status is validated although the invoice did not receive its index.
            The name of the invoice needs to match the name returned by SPV for the matching to work as intended.
        '''
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='5019882651', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        invoice.name = 'INV/2017/00001'
        # Reset the invoice and remove its index to trigger the matching by name to the success response
        invoice.l10n_ro_edi_index = False
        invoice.l10n_ro_edi_state = 'invoice_not_indexed'

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_index, '5019882651')
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_validated')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_index_not_in_messages(self):
        ''' Test that a sent invoice status not present in the messages returned by SPV is not updated.
        '''
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='INDEX', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_refusal(self):
        ''' Test that a sent invoice status is refused.
        '''
        # Create an invoice to match the failure response returned by the server
        invoice = self.create_move('out_invoice', l10n_ro_edi_index='5020592384', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_refused')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_refusal_held_non_indexed(self):
        ''' Test that non-indexed invoices that have been held for too long get refused.
        '''
        invoice = self.create_move('out_invoice', send=False)
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        invoice.name = 'INV/2017/00003'  # Skip 00001 and 00002 to avoid the validation due to similar invoice name
        invoice.l10n_ro_edi_state = 'invoice_not_indexed'

        self.assertEqual(invoice.l10n_ro_edi_index, False)

        with freeze_time(invoice.create_date + relativedelta(days=HOLDING_DAYS + 1)):
            self.env['account.move']._l10n_ro_edi_fetch_invoices()
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_not_indexed')

        with freeze_time(invoice.create_date + relativedelta(days=HOLDING_DAYS + 2)):
            self.env['account.move']._l10n_ro_edi_fetch_invoices()
        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_refused')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

    @patch('odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_synchronize_invoices', new=_patch_request_ciusro_synchronize_invoices)
    def test_ciusro_synchronize_invoices_not_indexed_with_duplicate_name(self):
        """ Test the edge case where 2 messages have the same invoice name but different indexes in
            their data. This scenario coupled with name matching where none of the two invoices received an index,
            we want all signatures added to the named invoices.
        """
        invoice = self.create_move('out_invoice', send=False)
        invoice.name = 'INV/2017/00002'
        self.env['l10n_ro_edi.document'].create({
            'invoice_id': invoice.id,
            'state': 'invoice_sent',
        })
        invoice.l10n_ro_edi_state = 'invoice_not_indexed'

        self.env['account.move']._l10n_ro_edi_fetch_invoices()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_validated')
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 2)
