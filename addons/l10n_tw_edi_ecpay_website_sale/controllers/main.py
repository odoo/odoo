import werkzeug


from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI
from odoo.addons.portal.controllers.portal import CustomerPortal


class EcpayInvoiceController(http.Controller):
    @http.route("/payment/ecpay/save_ecpay_info/<int:sale_order_id>", type="json", auth="public")
    def save_ecpay_info(self, sale_order_id, **kwargs):
        try:
            order = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        res = {}
        res["l10n_tw_edi_is_print"] = kwargs.get("printFlag", False)
        res["l10n_tw_edi_is_donate"] = kwargs.get("donateFlag", False)
        res["l10n_tw_edi_love_code"] = kwargs.get("loveCode", False)
        res["l10n_tw_edi_customer_identifier"] = kwargs.get("identifier", False)
        res["l10n_tw_edi_carrier_type"] = kwargs.get("CarrierType", False)
        res["l10n_tw_edi_carrier_number"] = kwargs.get("carrierNumber", False)
        res["l10n_tw_edi_customer_name"] = kwargs.get("customerName") if kwargs.get("customerName", False) else order.partner_id.name
        if kwargs.get("customerAddress", False):
            res["l10n_tw_edi_customer_address"] = kwargs.get("customerAddress")
        elif kwargs.get("customerAddress", False) == "":
            res["l10n_tw_edi_customer_address"] = " "
        else:
            res["l10n_tw_edi_customer_address"] = order.partner_id.contact_address
        res["l10n_tw_edi_customer_email"] = kwargs.get("customerEmail", False) if kwargs.get("customerEmail", False) != '' else order.partner_id.email
        res["l10n_tw_edi_customer_phone"] = kwargs.get("customerPhone", False) if kwargs.get("customerPhone", False) != '' else order.partner_id.phone
        order.write(res)
        return True

    @http.route("/payment/ecpay/check_carrier_number/<int:sale_order_id>", type="json", auth="public")
    def check_carrier_number(self, sale_order_id, **kwargs):
        try:
            _ = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound
        request_url, merchant_id, hashkey, hashIV = request.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "BarCode": kwargs.get("carrier_number", False),
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/CheckBarcode", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    @http.route("/payment/ecpay/check_love_code/<int:sale_order_id>", type="json", auth="public")
    def check_love_code(self, sale_order_id, **kwargs):
        try:
            _ = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        request_url, merchant_id, hashkey, hashIV = request.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "LoveCode": kwargs.get("love_code", False),
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/CheckLoveCode", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    @http.route("/payment/ecpay/check_tax_id/<int:sale_order_id>", type="json", auth="public")
    def check_tax_id(self, sale_order_id, **kwargs):
        try:
            _ = CustomerPortal._document_check_access(self, 'sale.order', sale_order_id, kwargs.get("access_token", False))
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound

        request_url, merchant_id, hashkey, hashIV = request.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "UnifiedBusinessNo": kwargs.get("identifier", False),
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/GetCompanyNameByTaxID", json_data)
        if response_data.get("RtnCode") == 1:
            return response_data.get("CompanyName")
        return False
