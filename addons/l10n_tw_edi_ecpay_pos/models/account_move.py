from odoo import api, models
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def l10n_tw_edi_check_mobile_barcode(self, text):
        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "BarCode": text,
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/CheckBarcode", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    @api.model
    def l10n_tw_edi_check_love_code(self, text):
        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "LoveCode": text,
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/CheckLoveCode", json_data)
        return response_data.get("RtnCode") == 1 and response_data.get("IsExist") == "Y"

    @api.model
    def l10n_tw_edi_check_tax_id(self, text):
        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "UnifiedBusinessNo": text,
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/GetCompanyNameByTaxID", json_data)
        if response_data.get("RtnCode") == 1:
            return response_data.get("CompanyName")
        return False
