# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError

from odoo.addons.l10n_tw_edi_ecpay.utils import call_ecpay_api


class PosSession(models.Model):
    _inherit = "pos.session"

    def l10n_tw_edi_check_mobile_barcode(self, text):
        self.ensure_one()
        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "BarCode": text,
        }
        response_data = call_ecpay_api("/CheckBarcode", json_data, self.company_id)
        if response_data.get("RtnCode") != 1 or response_data.get("IsExist") != "Y":
            raise UserError(self.env._("Mobile barcode is invalid!"))

    def l10n_tw_edi_check_love_code(self, text):
        self.ensure_one()
        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "LoveCode": text,
        }

        response_data = call_ecpay_api("/CheckLoveCode", json_data, self.company_id)
        if response_data.get("RtnCode") != 1 or response_data.get("IsExist") != "Y":
            raise UserError(self.env._("Love code is invalid!"))
