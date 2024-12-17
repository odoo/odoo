# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug


from odoo import http
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class EcpayInvoiceController(http.Controller):
    @http.route("/payment/ecpay/save_ecpay_info/<int:sale_order_id>", type="json", auth="public")
    def save_ecpay_info(self, sale_order_id, **kwargs):
        try:
            order = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        order.write({
            "l10n_tw_edi_is_print": kwargs.get("printFlag", False),
            "l10n_tw_edi_love_code": kwargs.get("loveCode", False),
            "l10n_tw_edi_carrier_type": kwargs.get("CarrierType", False),
            "l10n_tw_edi_carrier_number": kwargs.get("carrierNumber", False),
        })

        if "identifier" in kwargs:
            order.partner_id.vat = kwargs["identifier"]
        return True

    @http.route("/payment/ecpay/check_carrier_number/<int:sale_order_id>", type="json", auth="public")
    def check_carrier_number(self, sale_order_id, **kwargs):
        try:
            _ = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        json_data = {
            "MerchantID": request.env.company.sudo().l10n_tw_edi_ecpay_merchant_id,
            "BarCode": kwargs.get("carrier_number", False),
        }

        response_data = EcPayAPI(request.env.company).call_ecpay_api("/CheckBarcode", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    @http.route("/payment/ecpay/check_love_code/<int:sale_order_id>", type="json", auth="public")
    def check_love_code(self, sale_order_id, **kwargs):
        try:
            _ = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        json_data = {
            "MerchantID": request.env.company.sudo().l10n_tw_edi_ecpay_merchant_id,
            "LoveCode": kwargs.get("love_code", False),
        }

        response_data = EcPayAPI(request.env.company).call_ecpay_api("/CheckLoveCode", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    @http.route("/payment/ecpay/check_tax_id/<int:sale_order_id>", type="json", auth="public")
    def check_tax_id(self, sale_order_id, **kwargs):
        try:
            _ = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        json_data = {
            "MerchantID": request.env.company.sudo().l10n_tw_edi_ecpay_merchant_id,
            "UnifiedBusinessNo": kwargs.get("identifier", False),
        }

        response_data = EcPayAPI(request.env.company).call_ecpay_api("/GetCompanyNameByTaxID", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("CompanyName")
