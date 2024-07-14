import os
from contextlib import contextmanager, ExitStack
from unittest import SkipTest
from unittest.mock import patch

from odoo.addons.account_avatax.lib.avatax_client import AvataxClient
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import TransactionCase
from .mocked_invoice_1_response import generate_response as generate_response_invoice_1
from .mocked_invoice_2_response import generate_response as generate_response_invoice_2

NOTHING = object()


class TestAvataxCommon(TransactionCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        res = super().setUpClass(*args, **kwargs)
        cls.env.company.avalara_api_id = os.getenv("AVALARA_LOGIN_ID") or "AVALARA_LOGIN_ID"
        cls.env.company.avalara_api_key = os.getenv("AVALARA_API_KEY") or "AVALARA_API_KEY"
        cls.env.company.avalara_environment = 'sandbox'
        cls.env.company.avalara_commit = True

        # Update address of company
        company = cls.env.user.company_id
        company.write({
            'street': "250 Executive Park Blvd",
            'city': "San Francisco",
            'state_id': cls.env.ref("base.state_us_5").id,
            'country_id': cls.env.ref("base.us").id,
            'zip': "94134",
        })
        company.partner_id.avalara_partner_code = os.getenv("AVALARA_COMPANY_CODE") or "DEFAULT"

        cls.fp_avatax = cls.env['account.fiscal.position'].create({
            'name': 'Avatax',
            'is_avatax': True,
        })

        # Create partner with correct US address
        cls.partner = cls.env["res.partner"].create({
            'name': "Sale Partner",
            'street': "2280 Market St",
            'city': "San Francisco",
            'state_id': cls.env.ref("base.state_us_5").id,
            'country_id': cls.env.ref("base.us").id,
            'zip': "94114",
            'avalara_partner_code': 'CUST123456',
            'property_account_position_id': cls.fp_avatax.id,
        })

        return res

    @classmethod
    @contextmanager
    def _client_patched(cls, create_transaction_details=None, **kwargs):
        # Unused items are used through locals().
        # pylint: disable=possibly-unused-variable
        if kwargs.get('create_transaction') is None and create_transaction_details is not None:
            def create_transaction(self, transaction, include=None):
                return {
                    'lines': [{
                        'lineNumber': line['number'],
                        'details': create_transaction_details,
                    } for line in transaction['lines']],
                    'summary': create_transaction_details,
                }

        if kwargs.get('uncommit_transaction') is None:
            def uncommit_transaction(self, companyCode, transactionCode, include=None):
                return {}

        def request(self, method, *args, **kwargs):
            assert False, "Request not authorized in mock"

        fnames = {fname for fname in dir(AvataxClient) if not fname.startswith('_')} - {
            'add_credentials',
        }
        methods = {**{fname: None for fname in fnames}, **kwargs, **locals()}
        with ExitStack() as stack:
            for _patch in [
                patch(f'{AvataxClient.__module__}.AvataxClient.{fname}', methods[fname])
                for fname in fnames
            ]:
                stack.enter_context(_patch)
            yield

    @classmethod
    @contextmanager
    def _capture_request(cls, return_value=NOTHING, return_func=NOTHING):
        class Capture:
            val = None

            def capture_request(self, method, *args, **kwargs):
                self.val = kwargs
                if return_value is NOTHING:
                    return return_func(method, *args, **kwargs)
                return return_value

        capture = Capture()
        with patch(f'{AvataxClient.__module__}.AvataxClient.request', capture.capture_request):
            yield capture

    @classmethod
    @contextmanager
    def _skip_no_credentials(cls):
        if not os.getenv("AVALARA_LOGIN_ID") or not os.getenv("AVALARA_API_KEY") or not os.getenv("AVALARA_COMPANY_CODE"):
            raise SkipTest("no Avalara credentials")
        yield


class TestAccountAvataxCommon(TestAvataxCommon, AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        res = super().setUpClass(chart_template_ref)
        cls.product = cls.env["product.product"].create({
            'name': "Product",
            'default_code': 'PROD1',
            'barcode': '123456789',
            'list_price': 15.00,
            'standard_price': 15.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })
        cls.product_user = cls.env["product.product"].create({
            'name': "Odoo User",
            'list_price': 35.00,
            'standard_price': 35.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })
        cls.product_user_discound = cls.env["product.product"].create({
            'name': "Odoo User Initial Discount",
            'list_price': -5.00,
            'standard_price': -5.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })
        cls.product_accounting = cls.env["product.product"].create({
            'name': "Accounting",
            'list_price': 30.00,
            'standard_price': 30.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })
        cls.product_expenses = cls.env["product.product"].create({
            'name': "Expenses",
            'list_price': 15.00,
            'standard_price': 15.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })
        cls.product_invoicing = cls.env["product.product"].create({
            'name': "Invoicing",
            'list_price': 15.00,
            'standard_price': 15.00,
            'supplier_taxes_id': None,
            'avatax_category_id': cls.env.ref('account_avatax.DC010000').id,
        })

        # This tax is deliberately wrong with an amount of 1. This is used
        # to make sure we use the tax values that Avatax returns and not the tax values
        # Odoo computes (these values would be wrong if a user manually changes it for example).
        cls.example_tax = cls.env["account.tax"].create({
            'name': 'CA STATE TAX [06] (6.0000 %)',
            'company_id': cls.env.user.company_id.id,
            'amount': 1,
            'amount_type': 'percent',
        })

        return res

    @classmethod
    def _create_invoice(cls):
        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'fiscal_position_id': cls.fp_avatax.id,
            'invoice_date': '2020-01-01',
            'invoice_line_ids': [
                (0, 0, {'product_id': cls.product.id, 'price_unit': 100}),
            ]
        })
        invoice.action_post()
        return invoice

    @classmethod
    def _create_invoice_01_and_expected_response(cls):
        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'fiscal_position_id': cls.fp_avatax.id,
            'invoice_date': '2021-01-01',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': cls.product_user.id,
                    'tax_ids': None,
                    'price_unit': cls.product_user.list_price,
                }),
                (0, 0, {
                    'product_id': cls.product_user_discound.id,
                    'tax_ids': None,
                    'price_unit': cls.product_user_discound.list_price,
                }),
                (0, 0, {
                    'product_id': cls.product_accounting.id,
                    'tax_ids': None,
                    'price_unit': cls.product_accounting.list_price,
                }),
                (0, 0, {
                    'product_id': cls.product_expenses.id,
                    'tax_ids': None,
                    'price_unit': cls.product_expenses.list_price,
                }),
                (0, 0, {
                    'product_id': cls.product_invoicing.id,
                    'tax_ids': None,
                    'price_unit': cls.product_invoicing.list_price,
                }),
            ]
        })
        response = generate_response_invoice_1(invoice.invoice_line_ids)
        return invoice, response

    @classmethod
    def _create_invoice_02_and_expected_response(cls):
        invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'fiscal_position_id': cls.fp_avatax.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': cls.product_user.id,
                    'tax_ids': None,
                    'price_unit': cls.product_user.list_price,
                    'discount': 1 / 7 * 100,
                }),
                (0, 0, {
                    'product_id': cls.product_accounting.id,
                    'tax_ids': None,
                    'price_unit': cls.product_accounting.list_price,
                }),
                (0, 0, {
                    'product_id': cls.product_expenses.id,
                    'tax_ids': None,
                    'price_unit': cls.product_expenses.list_price,
                }),
                (0, 0, {
                    'product_id': cls.product_invoicing.id,
                    'tax_ids': None,
                    'price_unit': cls.product_invoicing.list_price,
                }),
            ]
        })
        response = generate_response_invoice_2(invoice.invoice_line_ids)
        return invoice, response
