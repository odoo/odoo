# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .test_edi_pos_order import L10nTWITestEdiPosOrder
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from unittest.mock import patch

CALL_API_METHOD = 'odoo.addons.l10n_tw_edi_ecpay.models.account_move.call_ecpay_api'
CALL_API_POS = 'odoo.addons.l10n_tw_edi_ecpay_pos.models.pos_order.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTWITestEdiPosOrderUI(L10nTWITestEdiPosOrder, TestPointOfSaleHttpCommon):
    def mock_ecpay_api(self, endpoint, params, company_id, is_b2b=False):
        """Mock EcPay API responses for tour tests."""
        mock_responses = {
            "/CheckBarcode": {"RtnCode": 1, "IsExist": "Y"},
            "/CheckLoveCode": {"RtnCode": 1, "IsExist": "Y"},
            "/Issue": {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            },
            "/GetIssue": {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            },
            "/GetCompanyNameByTaxID": {"RtnCode": 1, "CompanyName": "Test Company"}
        }
        return mock_responses.get(endpoint, {})

    def test_01_ecpay_b2c_check_mobile_barcode_tour(self):
        """Test input mobile barcode in ecpay popup"""
        def mock_check_mobile_barcode(instance, barcode):
            return True
        with patch('odoo.addons.l10n_tw_edi_ecpay_pos.models.pos_session.PosSession.l10n_tw_edi_check_mobile_barcode', new=mock_check_mobile_barcode), patch(CALL_API_METHOD, new=self.mock_ecpay_api):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'l10n_tw_edi_ecpay_pos.ecpay_b2c_check_mobile_barcode_tour', login="accountman")

    def test_02_ecpay_check_love_code_tour(self):
        """Test input love code in ecpay popup"""
        def mock_check_love_code(instance, love_code):
            return True
        with patch('odoo.addons.l10n_tw_edi_ecpay_pos.models.pos_session.PosSession.l10n_tw_edi_check_love_code', new=mock_check_love_code), patch(CALL_API_METHOD, new=self.mock_ecpay_api):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'l10n_tw_edi_ecpay_pos.ecpay_check_love_code_tour', login="accountman")

    def test_03_ecpay_check_print_invoice_tour(self):
        """Test default print invoice"""
        with patch(CALL_API_POS, new=self.mock_ecpay_api), patch(CALL_API_METHOD, new=self.mock_ecpay_api):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'l10n_tw_edi_ecpay_pos.ecpay_check_print_invoice_tour', login="accountman")

    def test_04_ecpay_toggle_invoice_tour(self):
        """Test toggling invoice option to off"""
        with patch(CALL_API_POS, new=self.mock_ecpay_api), patch(CALL_API_METHOD, new=self.mock_ecpay_api):
            self.main_pos_config.open_ui()
            self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'l10n_tw_edi_ecpay_pos.ecpay_toggle_invoice_tour', login="accountman")
