# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.l10n_vn_edi_viettel.tests.test_edi import TestVNEDI
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestVNEDIPOSTour(TestVNEDI, TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["l10n_vn_edi_viettel.sinvoice.template"].create({
            "name": "2/0024",
            "template_invoice_type": "2",
        })
        cls.symbol = cls.env["l10n_vn_edi_viettel.sinvoice.symbol"].create({
            "name": "C25MNK",
            "invoice_template_id": cls.template.id,
        })

    @staticmethod
    def _mock_sinvoice_send_request(method, url, json_data=None, params=None, headers=None, cookies=None):
        if url.endswith("/auth/login"):
            return {
                "access_token": "test_access_token",
                "expires_in": "3600",
            }, None

        if "InvoiceAPI/InvoiceWS/createInvoice" in url:
            return {
                "result": {
                    "reservationCode": "123456",
                    "invoiceNo": "K24TUT01",
                },
            }, None

        if "InvoiceAPI/InvoiceWS/searchInvoiceByTransactionUuid" in url:
            return {"result": []}, None

        if "InvoiceAPI/InvoiceUtilsWS/getInvoiceRepresentationFile" in url:
            return {
                "fileToBytes": "",
                "fileName": "sinvoice.pdf",
            }, None

        return {}, None

    def test_l10n_vn_edi_pos_config_error_tour(self):
        self.main_pos_config.write({
            "l10n_vn_auto_send_to_sinvoice": True,
            "l10n_vn_pos_symbol": False,
        })
        self.company.l10n_vn_pos_default_symbol = False

        with patch(
            "odoo.addons.l10n_vn_edi_viettel.models.account_move._l10n_vn_edi_send_request",
            side_effect=self._mock_sinvoice_send_request,
        ):
            self.start_pos_tour("L10nVnEdiPosConfigErrorTour")

    def test_l10n_vn_edi_pos_refund_reason_tour(self):
        self.company.l10n_vn_pos_default_symbol = self.symbol
        self.main_pos_config.write({
            "l10n_vn_auto_send_to_sinvoice": True,
            "l10n_vn_pos_symbol": self.symbol.id,
        })

        with patch(
            "odoo.addons.l10n_vn_edi_viettel.models.account_move._l10n_vn_edi_send_request",
            side_effect=self._mock_sinvoice_send_request,
        ):
            self.start_pos_tour("L10nVnEdiPosRefundReasonTour")
