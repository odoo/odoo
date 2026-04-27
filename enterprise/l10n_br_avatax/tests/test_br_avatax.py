# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import threading
from contextlib import contextmanager, nullcontext
from unittest import SkipTest
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_br_avatax.models.account_external_tax_mixin import AccountExternalTaxMixinL10nBR
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo import Command
from .mocked_invoice_response import generate_response
from .mocked_credit_note_response import generate_response as credit_note_generate_response

_logger = logging.getLogger(__name__)

DUMMY_SANDBOX_ID = "DUMMY_ID"
DUMMY_SANDBOX_KEY = "DUMMY_KEY"


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAvalaraBrCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('br')
    def setUpClass(cls):
        res = super().setUpClass()
        cls._setup_credentials()

        cls.fp_avatax = cls.env['account.fiscal.position'].create({
            'name': 'Avatax Brazil',
            'l10n_br_is_avatax': True,
        })

        cls._setup_partners()

        # Ensure the IAP service exists for this company. Otherwise, iap.account's get() method will fail.
        iap_service = cls.env.ref('l10n_br_avatax.iap_service_br_avatax')
        cls.env['iap.account'].create(
            {
                'service_id': iap_service.id,
                'company_ids': [(6, 0, cls.company_data['company'].ids)],
            }
        )

        cls._setup_products()

        return res

    @classmethod
    def _setup_credentials(cls):
        # Set real credentials here to run the integration tests
        cls.env.company.l10n_br_avatax_api_identifier = DUMMY_SANDBOX_ID
        cls.env.company.l10n_br_avatax_api_key = DUMMY_SANDBOX_KEY
        cls.env.company.l10n_br_avalara_environment = 'sandbox'

    @classmethod
    def _setup_partners(cls):
        company = cls.company_data['company']
        company.write({
            'street': 'Rua Marechal Deodoro 630',
            'street2': 'Edificio Centro Comercial Itália 24o Andar',
            'city': 'Curitiba',
            'state_id': cls.env.ref('base.state_br_pr').id,
            'country_id': cls.env.ref('base.br').id,
            'zip': '80010-010',
        })
        company.partner_id.l10n_br_tax_regime = 'individual'

        cls.partner = cls.env['res.partner'].create({
            'name': 'Avatax Brazil Test Partner',
            'street': 'Avenida SAP, 188',
            'street2': 'Cristo Rei',
            'city': 'São Leopoldo',
            'state_id': cls.env.ref('base.state_br_rs').id,
            'country_id': cls.env.ref('base.br').id,
            'zip': '93022-718',
            'property_account_position_id': cls.fp_avatax.id,
            'l10n_br_tax_regime': 'individual',
        })

    @classmethod
    def _setup_products(cls):
        common = {
            'l10n_br_ncm_code_id': cls.env.ref('l10n_br_avatax.49011000').id,
            'l10n_br_source_origin': '0',
            'l10n_br_sped_type': 'FOR PRODUCT',
            'l10n_br_use_type': 'use or consumption',
            'supplier_taxes_id': None,
        }

        cls.product = cls.env['product.product'].create({
            'name': 'Product',
            'default_code': 'PROD1',
            'barcode': '123456789',
            'list_price': 15.00,
            'standard_price': 15.00,
            **common,
        })
        cls.product_user = cls.env['product.product'].create({
            'name': 'Odoo User',
            'list_price': 35.00,
            'standard_price': 35.00,
            **common,
        })
        cls.product_user_discount = cls.env['product.product'].create({
            'name': 'Odoo User Initial Discount',
            'list_price': -5.00,
            'standard_price': -5.00,
            **common,
        })
        cls.product_accounting = cls.env['product.product'].create({
            'name': 'Accounting',
            'list_price': 30.00,
            'standard_price': 30.00,
            **common,
        })
        cls.product_expenses = cls.env['product.product'].create({
            'name': 'Expenses',
            'list_price': 15.00,
            'standard_price': 15.00,
            **common,
        })
        cls.product_invoicing = cls.env['product.product'].create({
            'name': 'Invoicing',
            'list_price': 15.00,
            'standard_price': 15.00,
            **common,
        })

    @classmethod
    @contextmanager
    def _skip_no_credentials(cls):
        company = cls.env.company
        if company.l10n_br_avatax_api_identifier == DUMMY_SANDBOX_ID or \
           company.l10n_br_avatax_api_key == DUMMY_SANDBOX_KEY or \
           company.l10n_br_avalara_environment != 'sandbox':
            raise SkipTest('no Avalara credentials')
        yield

    @classmethod
    @contextmanager
    def _capture_request_br(cls, return_value=None):
        with patch(f'{AccountExternalTaxMixinL10nBR.__module__}.AccountExternalTaxMixinL10nBR._l10n_br_iap_request', return_value=return_value) as mocked:
            yield mocked

    @classmethod
    def _create_invoice_01_and_expected_response(cls):
        products = (
            cls.product_user,
            cls.product_accounting,
            cls.product_expenses,
            cls.product_invoicing,
        )
        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'fiscal_position_id': cls.fp_avatax.id,
            'invoice_date': '2021-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': product.id,
                    'tax_ids': None,
                    'price_unit': product.list_price,
                }) for product in products
            ],
        })
        invoice.invoice_line_ids[0].discount = 10

        return invoice, generate_response(invoice.invoice_line_ids)


class TestAvalaraBrInvoiceCommon(TestAvalaraBrCommon):
    def assertInvoice(self, invoice, test_exact_response):
        self.assertEqual(
            len(invoice.invoice_line_ids.tax_ids),
            0,
            'There should be no tax rate on the line.'
        )

        self.assertRecordValues(invoice, [{
            'amount_total': 91.50,
            'amount_untaxed': 91.50,
            'amount_tax': 0.0,
        }])

        # When the external tests run this will need to do an IAP request which isn't possible in testing mode, see:
        # 7416acc111793ac1f7fd0dc653bb05cf7af28ebe
        with patch.object(threading.current_thread(), 'testing', False) if 'external_l10n' in self.test_tags else nullcontext():
            invoice.action_post()

        if test_exact_response:
            expected_amounts = {
                'amount_total': 91.50,
                'amount_untaxed': 91.50 - 10.98 - 5.02,
                'amount_tax': 10.98 + 5.02,
            }
            self.assertRecordValues(invoice, [expected_amounts])

            self.assertEqual(invoice.tax_totals['total_amount_currency'], expected_amounts['amount_total'])
            self.assertEqual(invoice.tax_totals['base_amount_currency'], expected_amounts['amount_untaxed'])

            self.assertEqual(len(invoice.tax_totals['subtotals']), 1)
            self.assertEqual(invoice.tax_totals['subtotals'][0]['base_amount_currency'], expected_amounts['amount_untaxed'])

            avatax_mapping = {avatax_line['lineCode']: avatax_line for avatax_line in test_exact_response['lines']}
            for line in invoice.invoice_line_ids:
                avatax_line = avatax_mapping[line.id]
                self.assertEqual(
                    line.price_total,
                    avatax_line['lineAmount'] - avatax_line['lineTaxedDiscount'],
                    f"Tax-included price doesn't match tax returned by Avatax for line {line.id} (product: {line.product_id.display_name})."
                )
                self.assertAlmostEqual(
                    line.price_subtotal,
                    avatax_line['lineNetFigure'] - avatax_line['lineTaxedDiscount'],
                    msg=f'Wrong Avatax amount for {line.id} (product: {line.product_id.display_name}), there is probably a mismatch between the test SO and the mocked response.'
                )

        else:
            for line in invoice.invoice_line_ids:
                product_name = line.product_id.display_name
                self.assertGreater(len(line.tax_ids), 0, 'Line with %s did not get any taxes set.' % product_name)

            self.assertGreater(invoice.amount_tax, 0.0, 'Invoice has a tax_amount of 0.0.')


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAvalaraBrInvoice(TestAvalaraBrInvoiceCommon):
    def test_01_invoice_br(self):
        invoice, response = self._create_invoice_01_and_expected_response()
        with self._capture_request_br(return_value=response):
            self.assertInvoice(invoice, test_exact_response=response)

    def test_02_non_brl(self):
        invoice, _ = self._create_invoice_01_and_expected_response()
        invoice.currency_id = self.env.ref('base.USD')

        with self.assertRaisesRegex(UserError, r'.* has to use Brazilian Real to calculate taxes with Avatax.'):
            self.assertInvoice(invoice, test_exact_response=None)

    def test_03_transport_cost(self):
        invoice, _ = self._create_invoice_01_and_expected_response()
        transport_cost_products = self.env['product.product'].create([{
            'name': 'freight',
            'list_price': 10.00,
            'l10n_br_transport_cost_type': 'freight',
        }, {
            'name': 'insurance',
            'list_price': 20.00,
            'l10n_br_transport_cost_type': 'insurance',
        }, {
            'name': 'other',
            'list_price': 30.00,
            'l10n_br_transport_cost_type': 'other',
        }])

        for product in transport_cost_products:
            self.env['account.move.line'].create({
                'product_id': product.id,
                'price_unit': product.list_price,
                'move_id': invoice.id,
            })

        # (line amount, freight, insurance, other) per line
        expected = [
            (35.00, 3.68, 7.37, 11.05),
            (30.00, 3.16, 6.32, 9.47),
            (15.00, 1.58, 3.16, 4.74),
            (15.00, 1.58, 3.15, 4.74), # note that the insurance amount is different from the line above to ensure the total adds up to 20
        ]

        api_request = invoice._l10n_br_get_calculate_payload()
        actual_lines = api_request['lines']
        self.assertEqual(len(expected), len(actual_lines), 'Different amount of expected and actual lines.')

        for expected, line in zip(expected, actual_lines):
            amount, freight, insurance, other = expected
            self.assertEqual(amount, line['lineAmount'])
            self.assertEqual(freight, line['freightAmount'])
            self.assertEqual(insurance, line['insuranceAmount'])
            self.assertEqual(other, line['otherCostAmount'])

    def test_04_negative_line(self):
        invoice, _ = self._create_invoice_01_and_expected_response()
        self.env['account.move.line'].create({
            'product_id': self.product_user_discount.id,
            'move_id': invoice.id,
            'price_unit': -1_000.00,
        })

        with self._capture_request_br(), \
             self.assertRaisesRegex(UserError, "Avatax Brazil doesn't support negative lines."):
            invoice.action_post()

    def test_05_credit_note(self):
        invoice, response = self._create_invoice_01_and_expected_response()
        with self._capture_request_br(return_value=response):
            invoice.action_post()

        credit_note_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'journal_id': invoice.journal_id.id,
        })
        credit_note_wizard.reverse_moves()

        credit_note = self.env['account.move'].search([('reversed_entry_id', '=', invoice.id)])
        self.assertTrue(credit_note, "A credit note should have been created.")

        payload = credit_note._l10n_br_get_calculate_payload()
        self.assertEqual(payload['header']['operationType'], 'salesReturn', 'The operationType for credit notes should be returnSales.')
        self.assertEqual(payload['header']['invoicesRefs'][0]['documentCode'], f'account.move_{invoice.id}', 'The credit note should reference the original invoice.')

    def test_06_service_invoice_with_installments(self):
        """Test that service invoices with installments clear tax_ids when using Avalara. It's necessary because Avalara
        expects installments to be sent without taxes for service invoices."""
        invoice, response = self._create_invoice_01_and_expected_response()
        rio_city = self.env.ref("l10n_br.city_br_002")

        invoice.invoice_payment_term_id = self.pay_terms_b.id
        invoice.l10n_latam_document_type_id = self.env.ref("l10n_br.dt_SE").id
        invoice.partner_id.city_id = rio_city

        # Mark all products as services and assign service code
        for line in invoice.invoice_line_ids:
            line.tax_ids = self.tax_sale_a
            line.product_id.write({
                'type': 'service',
                'l10n_br_property_service_code_origin_id': self.env['l10n_br.service.code'].create({
                    'code': '12345',
                    'city_id': rio_city.id,
                }),
            })

        # Ensure there's a tax amount
        self.assertGreater(invoice.amount_tax, 0, "There should be a tax amount on this invoice.")

        with self._capture_request_br(return_value=response) as captured:
            invoice._get_external_taxes()

        expected_untaxed_terms = invoice.invoice_payment_term_id._compute_terms(
            invoice.date,
            invoice.currency_id,
            invoice.company_id,
            tax_amount=0,
            tax_amount_currency=0,
            sign=1,
            untaxed_amount=invoice.amount_untaxed,
            untaxed_amount_currency=invoice.amount_untaxed,
        )

        self.assertEqual(
            [installment['grossValue'] for installment in captured.call_args[0][1]['header']['payment']['installment']],
            [term['company_amount'] for term in expected_untaxed_terms['line_ids']],
            "Installments should be sent without taxes."
        )

    def test_07_credit_note_with_included_tax(self):
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'PROD2',
            'list_price': 800.00,
            'standard_price': 800.00,
            'l10n_br_ncm_code_id': self.env.ref('l10n_br_avatax.02062990').id,
            'l10n_br_source_origin': '0',
            'l10n_br_sped_type': 'FOR PRODUCT',
            'l10n_br_use_type': 'production',
            'supplier_taxes_id': None,
        })

        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner.id,
            'fiscal_position_id': self.fp_avatax.id,
            'invoice_date': '2021-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': product.id,
                    'tax_ids': None,
                    'price_unit': product.list_price,
                }),
            ],
        })

        response = credit_note_generate_response(credit_note.invoice_line_ids)
        with self._capture_request_br(return_value=response):
            credit_note.action_post()

        expected_amounts = {
            'amount_total': 800.0,
            'amount_untaxed': 704.0,
            'amount_tax': 96.0,
        }
        self.assertRecordValues(credit_note, [expected_amounts])
        self.assertEqual(credit_note.tax_totals['total_amount_currency'], expected_amounts['amount_total'])
        self.assertEqual(credit_note.tax_totals['base_amount_currency'], expected_amounts['amount_untaxed'])


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestAvalaraBrSettings(TestAvalaraBrInvoiceCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('br')
    def setUpClass(cls):
        super().setUpClass()
        cls.settings = cls.env['res.config.settings'].create({})

    def test_01_create_account_success(self):
        return_value = {
            'avalara_api_id': 'API_ID',
            'avalara_api_key': 'API_KEY',
        }
        with self._capture_request_br(return_value=return_value):
            self.settings.create_account()

        self.assertRecordValues(self.env.company, [{
            'l10n_br_avatax_api_identifier': 'API_ID',
            'l10n_br_avatax_api_key': 'API_KEY',
        }])

    def test_02_create_account_error_type_1(self):
        return_value = {
            'message': 'One or more errors occurred. (CEP \'32516-076\' not found)',
            'isError': True,
        }
        with self._capture_request_br(return_value=return_value), \
             self.assertRaisesRegex(UserError, r'One or more errors occurred. \(CEP \'32516-076\' not found\)'):
            self.settings.create_account()

        return_value = {
            'message': 'An unhandled error occurred. Trace ID: xxx',
            'isError': True
        }
        with self._capture_request_br(return_value=return_value), \
             self.assertRaisesRegex(UserError, 'Please ensure the address on your company is correct'):
            self.settings.create_account()

    def test_03_create_account_error_type_2(self):
        return_value = {
            'message': '{"errors":{"Login do usuário master":["Login já utlizado"]},"title":"One or more validation errors occurred.","status":400,"traceId":"0HMPVCEB27KLU:000000E5"}',
            'isError': True,
        }

        with self._capture_request_br(return_value=return_value), \
             self.assertRaisesRegex(UserError, 'Login já utlizado'):
            self.settings.create_account()

    def test_04_no_false(self):
        """ Do not send "false" to the API for empty fields. It will populate "false" in some of the fields on Avatax's side
        and cause issues during EDI. """
        with self._capture_request_br(return_value={}) as mocked_request:
            self.settings.create_account()

        for k, v in mocked_request.call_args[0][1].items():
            self.assertNotEqual(v, False, f"{k} was False instead of empty string")


@tagged('external_l10n', 'external', '-at_install', 'post_install', '-standard')
class TestAvalaraBrInvoiceIntegration(TestAvalaraBrInvoiceCommon):
    def test_01_invoice_integration_br(self):
        with self._skip_no_credentials():
            invoice, _ = self._create_invoice_01_and_expected_response()
            self.assertInvoice(invoice, test_exact_response=False)
