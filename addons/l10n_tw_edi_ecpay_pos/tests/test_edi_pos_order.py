# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from freezegun import freeze_time

from odoo.addons.l10n_tw_edi_ecpay.tests.test_edi import L10nTWITestEdi
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from unittest.mock import patch

CALL_API_METHOD = 'odoo.addons.l10n_tw_edi_ecpay.models.account_move.call_ecpay_api'
CALL_API_POS = 'odoo.addons.l10n_tw_edi_ecpay_pos.models.pos_session.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTWITestEdiPosOrder(L10nTWITestEdi, TestPoSCommon):

    @classmethod
    @TestPoSCommon.setup_country('tw')
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.product_a.available_in_pos = True
        cls.company.country_id = cls.env.ref('base.tw')

    @contextmanager
    def with_pos_session(self):
        session = self.open_new_session(0.0)
        yield session  # noqa: RUF075
        session.post_closing_cash_details(0.0)
        session.close_session_from_ui()

    def _create_order(self, ui_data):
        order_data = self.create_ui_order_data(**ui_data)
        results = self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].browse(results['pos.order'][0]['id'])

    @freeze_time("2025-01-06 15:00:00")
    def test_01_pos_data_to_invoice(self):
        """Test the data passed from the PoS to the invoice."""
        with self.with_pos_session():
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product_a, 1)],
                'payments': [(self.cash_pm1, 1050.0)],
                'customer': self.partner_a,
            })
            order.write({
                'l10n_tw_edi_is_print': True,
                'l10n_tw_edi_love_code': False,
                'l10n_tw_edi_carrier_type': "1",
                "l10n_tw_edi_carrier_number": "12345678",
            })
            with patch(CALL_API_METHOD, new=self._test_01_mock):
                order.action_pos_order_invoice()
            invoice = order.account_move

            self.assertEqual(invoice.l10n_tw_edi_is_print, order.l10n_tw_edi_is_print)
            self.assertEqual(invoice.l10n_tw_edi_love_code, order.l10n_tw_edi_love_code)
            self.assertEqual(invoice.l10n_tw_edi_carrier_type, order.l10n_tw_edi_carrier_type)
            self.assertEqual(invoice.l10n_tw_edi_carrier_number, order.l10n_tw_edi_carrier_number)

    @freeze_time("2025-01-06 15:00:00")
    def test_02_invoiced_order_then_invoiced_refund(self):
        with self.with_pos_session():
            # Invoice an order.
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product_a, 1)],
                'payments': [(self.bank_pm1, 1050.0)],
                'customer': self.partner_a,
            })
            with patch(CALL_API_METHOD, new=self._test_02_mock):
                order.action_pos_order_invoice()
            invoice = order.account_move
            refund = self.env['pos.order'].browse(order.refund()['res_id'])
            with patch(CALL_API_METHOD, new=self._test_02_mock):
                refund.action_pos_order_invoice()

            self.assertEqual(refund.account_move.reversed_entry_id, invoice)
            self.assertEqual(refund.account_move.l10n_tw_edi_ecpay_invoice_id, invoice.l10n_tw_edi_ecpay_invoice_id)
            self.assertEqual(refund.account_move.l10n_tw_edi_invoice_create_date, invoice.l10n_tw_edi_invoice_create_date)

    def test_03_invoice_month_calculation(self):
        """Test the Taiwanese invoice billing period calculation."""
        order = self.env['pos.order']

        month_str = order._l10n_tw_edi_set_invoice_month("2026-01-15 10:00:00")
        self.assertEqual(month_str, "115年1-2月")

        month_str = order._l10n_tw_edi_set_invoice_month("2026-02-15 10:00:00")
        self.assertEqual(month_str, "115年1-2月")

        month_str = order._l10n_tw_edi_set_invoice_month("2026-11-15 10:00:00")
        self.assertEqual(month_str, "115年11-12月")

        month_str = order._l10n_tw_edi_set_invoice_month("2026-12-15 10:00:00")
        self.assertEqual(month_str, "115年11-12月")

    def test_04_barcode_validation_valid(self):
        """Test mobile barcode validation with valid barcode."""
        with self.with_pos_session() as session:
            def valid_barcode_mock(endpoint, params, company_id):
                if endpoint == "/CheckBarcode":
                    return {
                        "RtnCode": 1,
                        "IsExist": "Y"
                    }
                raise UserError(f'Unexpected endpoint: {endpoint}')

            with patch(CALL_API_POS, new=valid_barcode_mock):
                session.l10n_tw_edi_check_mobile_barcode("/ABC1234")

    def test_05_love_code_validation_valid(self):
        """Test love code validation with valid code."""
        with self.with_pos_session() as session:
            def valid_love_code_mock(endpoint, params, company_id):
                if endpoint == "/CheckLoveCode":
                    return {
                        "RtnCode": 1,
                        "IsExist": "Y"
                    }
                raise UserError(f'Unexpected endpoint: {endpoint}')

            with patch(CALL_API_POS, new=valid_love_code_mock):
                session.l10n_tw_edi_check_love_code("1234567")

    def _test_01_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == "/GetIssue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.product_a.lst_price,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
        elif endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_02_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == "/GetIssue":
            return_data = {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.product_a.lst_price,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
            return return_data
        elif endpoint == "/Allowance":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IA_Allow_No": "20250106000000021",
                "IA_Invoice_No": "AB11100099",
                "IA_Date": "2025-01-06 23:00:00",
                "IA_Remain_Allowance_Amt": 0,
            }
        elif endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
