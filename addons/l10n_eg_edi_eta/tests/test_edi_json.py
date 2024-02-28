import json
from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged

from .common import TestEGEdiCommon

ETA_TEST_RESPONSE = {
    'l10n_eg_uuid': 'UUIDXIL9182712KMHJQ',
    'l10n_eg_long_id': 'LIDMN12132LASKXXA',
    'l10n_eg_internal_id': 'INTLA1212MMKA12',
    'l10n_eg_hash_key': 'BaK12lX1kASdma12',
    'l10n_eg_submission_number': '12125523452353',
}
ETA_TEST_SIGNATURES = [{'1': '1'}]
COMMON_REQUEST_DICT = {
    'issuer': {
        'address': {
            'country': 'EG',
            'governate': 'Cairo',
            'regionCity': 'Iswan',
            'street': '12th dec. street',
            'buildingNumber': '10',
            'postalCode': '',
            'branchID': '0',
        },
        'name': 'branch partner',
        'type': 'B',
        'id': '918KKL1',
    },
    'documentType': 'i',
    'documentTypeVersion': '1.0',
    'dateTimeIssued': '2022-03-15T00:00:00Z',
    'taxpayerActivityCode': '8121',
    'internalID': 'INV/2022/00001',
    'totalDiscountAmount': 0.0,
    'extraDiscountAmount': 0.0,
    'totalItemsDiscountAmount': 0.0,
    'signatures': ETA_TEST_SIGNATURES,
}

def mocked_action_post_sign_invoices(self):
    for invoice in self:
        eta_invoice = self.env['account.edi.format']._l10n_eg_eta_prepare_eta_invoice(self)
        eta_invoice['signatures'] = ETA_TEST_SIGNATURES
        attachment = self.env['ir.attachment'].create(
            {
                'name': ('ETA_INVOICE_DOC_%s', invoice.name),
                'res_id': invoice.id,
                'res_model': invoice._name,
                'type': 'binary',
                'raw': json.dumps(dict(request=eta_invoice)),
                'mimetype': 'application/json',
                'description': ('Egyptian Tax authority JSON invoice generated for %s.', invoice.name),
            }
        )
        invoice.l10n_eg_eta_json_doc_id = attachment.id
    return True


def mocked_l10n_eg_edi_post_invoice_web_service(self, invoice):
    eta_invoice_json = json.loads(invoice.l10n_eg_eta_json_doc_id.raw)
    eta_invoice_json['response'] = ETA_TEST_RESPONSE
    invoice.l10n_eg_eta_json_doc_id.raw = json.dumps(eta_invoice_json)
    return {'success': True, 'attachment': invoice.l10n_eg_eta_json_doc_id}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiJson(TestEGEdiCommon):

    def test_1_simple_test_local_parter_no_tax(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 100.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'tax_ids': [],
                    },
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 200.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'tax_ids': [],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'EG',
                                'governate': 'Cairo',
                                'regionCity': 'Iswan',
                                'street': '12th dec. street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_a',
                            'type': 'B',
                            'id': 'BE0477472701',
                        },
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 100.0},
                                'discount': {'rate': 0.0, 'amount': 0.0},
                                'taxableItems': [],
                                'salesTotal': 100.0,
                                'netTotal': 100.0,
                                'total': 100.0,
                            },
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 200.0},
                                'discount': {'rate': 0.0, 'amount': 0.0},
                                'taxableItems': [],
                                'salesTotal': 200.0,
                                'netTotal': 200.0,
                                'total': 200.0,
                            },
                        ],
                        'taxTotals': [],
                        'totalSalesAmount': 300.0,
                        'netAmount': 300.0,
                        'totalAmount': 300.0,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_2_simple_test_local_parter_vat_14(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 120.99,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_standard_sale_14').ids)],
                    },
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 999.99,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_standard_sale_14').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'EG',
                                'governate': 'Cairo',
                                'regionCity': 'Iswan',
                                'street': '12th dec. street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_a',
                            'type': 'B',
                            'id': 'BE0477472701',
                        },
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 120.99},
                                'discount': {'rate': 0.0, 'amount': -0.0},
                                'taxableItems': [{'taxType': 'T1', 'amount': 16.94, 'subType': 'V009', 'rate': 14.0}],
                                'salesTotal': 120.99,
                                'netTotal': 120.99,
                                'total': 137.93,
                            },
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 999.99},
                                'discount': {'rate': 0.0, 'amount': 0.0},
                                'taxableItems': [{'taxType': 'T1', 'amount': 140.0, 'subType': 'V009', 'rate': 14.0}],
                                'salesTotal': 999.99,
                                'netTotal': 999.99,
                                'total': 1139.99,
                            },
                        ],
                        'taxTotals': [{'taxType': 'T1', 'amount': 156.94}],
                        'totalSalesAmount': 1120.98,
                        'netAmount': 1120.98,
                        'totalAmount': 1277.92,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_3_simple_test_local_parter_vat_14_discount_credit_note(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                move_type='out_refund',
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 12.0,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'discount': 10.0,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_standard_sale_14').ids)],
                    },
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 99.96,
                        'quantity': 1.0,
                        'discount': 10.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_standard_sale_14').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'EG',
                                'governate': 'Cairo',
                                'regionCity': 'Iswan',
                                'street': '12th dec. street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_a',
                            'type': 'B',
                            'id': 'BE0477472701',
                        },
                        'internalID': 'RINV/2022/00001',
                        'documentType': 'c',
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 12.0},
                                'discount': {'rate': 10.0, 'amount': 1.2},
                                'taxableItems': [{'taxType': 'T1', 'amount': 1.51, 'subType': 'V009', 'rate': 14.0}],
                                'salesTotal': 12.0,
                                'netTotal': 10.8,
                                'total': 12.31,
                            },
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 99.95556},
                                'discount': {'rate': 10.0, 'amount': 9.99556},
                                'taxableItems': [{'taxType': 'T1', 'amount': 12.59, 'subType': 'V009', 'rate': 14.0}],
                                'salesTotal': 99.95556,
                                'netTotal': 89.96,
                                'total': 102.55,
                            },
                        ],
                        'taxTotals': [{'taxType': 'T1', 'amount': 14.1}],
                        'totalDiscountAmount': 11.19556,
                        'totalSalesAmount': 111.95556,
                        'netAmount': 100.76,
                        'totalAmount': 114.86,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_4_simple_test_local_parter_vat_14_discount(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 120.99,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'discount': 10.0,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_standard_sale_14').ids)],
                    },
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 999.55,
                        'quantity': 1.0,
                        'discount': 10.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_standard_sale_14').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'EG',
                                'governate': 'Cairo',
                                'regionCity': 'Iswan',
                                'street': '12th dec. street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_a',
                            'type': 'B',
                            'id': 'BE0477472701',
                        },
                        'documentType': 'i',
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 120.98889},
                                'discount': {'rate': 10.0, 'amount': 12.09889},
                                'taxableItems': [{'taxType': 'T1', 'amount': 15.24, 'subType': 'V009', 'rate': 14.0}],
                                'salesTotal': 120.98889,
                                'netTotal': 108.89,
                                'total': 124.13,
                            },
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 999.55556},
                                'discount': {'rate': 10.0, 'amount': 99.95556},
                                'taxableItems': [{'taxType': 'T1', 'amount': 125.94, 'subType': 'V009', 'rate': 14.0}],
                                'salesTotal': 999.55556,
                                'netTotal': 899.6,
                                'total': 1025.54,
                            },
                        ],
                        'taxTotals': [{'taxType': 'T1', 'amount': 141.18}],
                        'totalDiscountAmount': 112.05445,
                        'totalSalesAmount': 1120.54445,
                        'netAmount': 1008.49,
                        'totalAmount': 1149.67,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_5_simple_test_foreign_partner_exempt_discount(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 120.99,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'discount': 10.0,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                    {
                        'product_id': self.product_b.id,
                        'price_unit': 999.55,
                        'quantity': 5.0,
                        'discount': 13.0,
                        'product_uom_id': self.env.ref('uom.product_uom_cm').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'US',
                                'governate': 'New York',
                                'regionCity': 'New York City',
                                'street': '5th avenue street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_b',
                            'type': 'F',
                            'id': 'ESF35999705',
                        },
                        'documentType': 'i',
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 120.98889},
                                'discount': {'rate': 10.0, 'amount': 12.09889},
                                'taxableItems': [{'taxType': 'T1', 'amount': 0.0, 'subType': 'V003', 'rate': 0.0}],
                                'salesTotal': 120.98889,
                                'netTotal': 108.89,
                                'total': 108.89,
                            },
                            {
                                'description': 'product_b',
                                'itemType': 'EGS',
                                'itemCode': 'EG-EGS-TEST',
                                'unitType': 'CMT',
                                'quantity': 5.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {'currencySold': 'EGP', 'amountEGP': 999.54943},
                                'discount': {'rate': 13.0, 'amount': 649.70713},
                                'taxableItems': [{'taxType': 'T1', 'amount': 0.0, 'subType': 'V003', 'rate': 0.0}],
                                'salesTotal': 4997.74713,
                                'netTotal': 4348.04,
                                'total': 4348.04,
                            },
                        ],
                        'taxTotals': [{'taxType': 'T1', 'amount': 0.0}],
                        'totalDiscountAmount': 661.80602,
                        'totalSalesAmount': 5118.73602,
                        'netAmount': 4456.93,
                        'totalAmount': 4456.93,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_6_simple_test_foreign_parter_exempt_discount_foreign_currency(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                currency_id=self.currency_aed_id.id,
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 120.99,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'discount': 10.0,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                    {
                        'product_id': self.product_b.id,
                        'price_unit': 999.55,
                        'quantity': 5.0,
                        'discount': 13.0,
                        'product_uom_id': self.env.ref('uom.product_uom_cm').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'US',
                                'governate': 'New York',
                                'regionCity': 'New York City',
                                'street': '5th avenue street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_b',
                            'type': 'F',
                            'id': 'ESF35999705',
                        },
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {
                                    'currencySold': 'AED',
                                    'amountEGP': 610.68889,
                                    'currencyExchangeRate': 5.04748,
                                    'amountSold': 120.99,
                                },
                                'discount': {'rate': 10.0, 'amount': 61.06889},
                                'taxableItems': [{'taxType': 'T1', 'amount': 0.0, 'subType': 'V003', 'rate': 0.0}],
                                'salesTotal': 610.68889,
                                'netTotal': 549.62,
                                'total': 549.62,
                            },
                            {
                                'description': 'product_b',
                                'itemType': 'EGS',
                                'itemCode': 'EG-EGS-TEST',
                                'unitType': 'CMT',
                                'quantity': 5.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {
                                    'currencySold': 'AED',
                                    'amountEGP': 5045.24598,
                                    'currencyExchangeRate': 5.04748,
                                    'amountSold': 999.55,
                                },
                                'discount': {'rate': 13.0, 'amount': 3279.40989},
                                'taxableItems': [{'taxType': 'T1', 'amount': 0.0, 'subType': 'V003', 'rate': 0.0}],
                                'salesTotal': 25226.22989,
                                'netTotal': 21946.82,
                                'total': 21946.82,
                            },
                        ],
                        'taxTotals': [{'taxType': 'T1', 'amount': 0.0}],
                        'totalDiscountAmount': 3340.47878,
                        'totalSalesAmount': 25836.91878,
                        'netAmount': 22496.44,
                        'totalAmount': 22496.44,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_7_simple_test_foreign_parter_exempt_discount_foreign_currency_credit_note(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                move_type='out_invoice',
                currency_id=self.currency_aed_id.id,
                partner_id=self.partner_b.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 100.0,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'discount': 10.0,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                    {
                        'product_id': self.product_b.id,
                        'price_unit': 100.35,
                        'quantity': 5.0,
                        'discount': 13.0,
                        'product_uom_id': self.env.ref('uom.product_uom_cm').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            self.assertEqual(
                json_file,
                {
                    'request': {**COMMON_REQUEST_DICT,
                        'receiver': {
                            'address': {
                                'country': 'US',
                                'governate': 'New York',
                                'regionCity': 'New York City',
                                'street': '5th avenue street',
                                'buildingNumber': '12',
                                'postalCode': '',
                            },
                            'name': 'partner_b',
                            'type': 'F',
                            'id': 'ESF35999705',
                        },
                        'invoiceLines': [
                            {
                                'description': 'product_a',
                                'itemType': 'GS1',
                                'itemCode': '1KGS1TEST',
                                'unitType': 'C62',
                                'quantity': 1.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {
                                    'currencySold': 'AED',
                                    'amountEGP': 504.75556,
                                    'currencyExchangeRate': 5.04756,
                                    'amountSold': 100.0,
                                },
                                'discount': {'rate': 10.0, 'amount': 50.47556},
                                'taxableItems': [{'taxType': 'T1', 'amount': 0.0, 'subType': 'V003', 'rate': 0.0}],
                                'salesTotal': 504.75556,
                                'netTotal': 454.28,
                                'total': 454.28,
                            },
                            {
                                'description': 'product_b',
                                'itemType': 'EGS',
                                'itemCode': 'EG-EGS-TEST',
                                'unitType': 'CMT',
                                'quantity': 5.0,
                                'internalCode': '',
                                'valueDifference': 0.0,
                                'totalTaxableFees': 0.0,
                                'itemsDiscount': 0.0,
                                'unitValue': {
                                    'currencySold': 'AED',
                                    'amountEGP': 506.51494,
                                    'currencyExchangeRate': 5.04756,
                                    'amountSold': 100.35,
                                },
                                'discount': {'rate': 13.0, 'amount': 329.23471},
                                'taxableItems': [{'taxType': 'T1', 'amount': 0.0, 'subType': 'V003', 'rate': 0.0}],
                                'salesTotal': 2532.57471,
                                'netTotal': 2203.34,
                                'total': 2203.34,
                            },
                        ],
                        'taxTotals': [{'taxType': 'T1', 'amount': 0.0}],
                        'totalDiscountAmount': 379.71027,
                        'totalSalesAmount': 3037.33027,
                        'netAmount': 2657.62,
                        'totalAmount': 2657.62,
                    },
                    'response': ETA_TEST_RESPONSE,
                },
            )

    def test_8_test_serialization_function(self):
        with freeze_time(self.frozen_today), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_move.AccountMove.action_post_sign_invoices',
            new=mocked_action_post_sign_invoices,
        ), patch(
            'odoo.addons.l10n_eg_edi_eta.models.account_edi_format.AccountEdiFormat._l10n_eg_edi_post_invoice_web_service',
            new=mocked_l10n_eg_edi_post_invoice_web_service,
        ):
            invoice = self.create_invoice(
                move_type='out_invoice',
                currency_id=self.currency_aed_id.id,
                partner_id=self.partner_c.id,
                invoice_line_ids=[
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 100.0,
                        'quantity': 1.0,
                        'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                        'discount': 10.0,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                    {
                        'product_id': self.product_b.id,
                        'price_unit': 100.35,
                        'quantity': 5.0,
                        'discount': 13.0,
                        'product_uom_id': self.env.ref('uom.product_uom_cm').id,
                        'tax_ids': [(6, 0, self.env.ref(f'l10n_eg.{self.env.company.id}_eg_exempt_sale').ids)],
                    },
                ],
            )
            invoice.action_post()
            invoice.action_post_sign_invoices()

            generated_files = self._process_documents_web_services(invoice, {'eg_eta'})
            self.assertTrue(generated_files)
            json_file = json.loads(generated_files[0])
            serialized_string = self.env['l10n_eg_edi.thumb.drive']._serialize_for_signing(json_file['request'])
            self.assertEqual(serialized_string, '"ISSUER""ADDRESS""COUNTRY""EG""GOVERNATE""Cairo""REGIONCITY""Iswan""STREET""12th dec. street""BUILDINGNUMBER""10""POSTALCODE""""BRANCHID""0""NAME""branch partner""TYPE""B""ID""918KKL1""RECEIVER""ADDRESS""COUNTRY""EG""GOVERNATE""Cairo""REGIONCITY""Iswan""STREET""12th dec. street""BUILDINGNUMBER""12""POSTALCODE""""NAME""عميل 1""TYPE""B""ID""EG11231212""DOCUMENTTYPE""i""DOCUMENTTYPEVERSION""1.0""DATETIMEISSUED""2022-03-15T00:00:00Z""TAXPAYERACTIVITYCODE""8121""INTERNALID""INV/2022/00001""INVOICELINES""INVOICELINES""DESCRIPTION""product_a""ITEMTYPE""GS1""ITEMCODE""1KGS1TEST""UNITTYPE""C62""QUANTITY""1.0""INTERNALCODE""""VALUEDIFFERENCE""0.0""TOTALTAXABLEFEES""0.0""ITEMSDISCOUNT""0.0""UNITVALUE""CURRENCYSOLD""AED""AMOUNTEGP""504.75556""CURRENCYEXCHANGERATE""5.04756""AMOUNTSOLD""100.0""DISCOUNT""RATE""10.0""AMOUNT""50.47556""TAXABLEITEMS""TAXABLEITEMS""TAXTYPE""T1""AMOUNT""0.0""SUBTYPE""V003""RATE""0.0""SALESTOTAL""504.75556""NETTOTAL""454.28""TOTAL""454.28""INVOICELINES""DESCRIPTION""product_b""ITEMTYPE""EGS""ITEMCODE""EG-EGS-TEST""UNITTYPE""CMT""QUANTITY""5.0""INTERNALCODE""""VALUEDIFFERENCE""0.0""TOTALTAXABLEFEES""0.0""ITEMSDISCOUNT""0.0""UNITVALUE""CURRENCYSOLD""AED""AMOUNTEGP""506.51494""CURRENCYEXCHANGERATE""5.04756""AMOUNTSOLD""100.35""DISCOUNT""RATE""13.0""AMOUNT""329.23471""TAXABLEITEMS""TAXABLEITEMS""TAXTYPE""T1""AMOUNT""0.0""SUBTYPE""V003""RATE""0.0""SALESTOTAL""2532.57471""NETTOTAL""2203.34""TOTAL""2203.34""TAXTOTALS""TAXTOTALS""TAXTYPE""T1""AMOUNT""0.0""TOTALDISCOUNTAMOUNT""379.71027""TOTALSALESAMOUNT""3037.33027""NETAMOUNT""2657.62""TOTALAMOUNT""2657.62""EXTRADISCOUNTAMOUNT""0.0""TOTALITEMSDISCOUNTAMOUNT""0.0""SIGNATURES""SIGNATURES""1""1"')
