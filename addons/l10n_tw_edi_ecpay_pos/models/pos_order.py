# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI
from odoo.exceptions import UserError


class PoSOrder(models.Model):
    _inherit = "pos.order"

    l10n_tw_edi_is_print = fields.Boolean(string="Print")
    l10n_tw_edi_love_code = fields.Char(string="Love Code")
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[
            ("1", "ECpay e-invoice carrier"),
            ("2", "Citizen Digital Certificate"),
            ("3", "Mobile Barcode"),
            ("4", "EasyCard"),
            ("5", "iPass"),
        ],
    )
    l10n_tw_edi_carrier_number = fields.Char(string="Carrier Number")
    l10n_tw_edi_carrier_number_2 = fields.Char(string="Carrier Number 2")

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        vals.update({
            'l10n_tw_edi_is_print': self.l10n_tw_edi_is_print,
            'l10n_tw_edi_love_code': self.l10n_tw_edi_love_code,
            'l10n_tw_edi_carrier_type': self.l10n_tw_edi_carrier_type,
            'l10n_tw_edi_carrier_number': self.l10n_tw_edi_carrier_number,
            'l10n_tw_edi_carrier_number_2': self.l10n_tw_edi_carrier_number_2,
        })
        return vals

    def _generate_pos_order_invoice(self):
        res = super()._generate_pos_order_invoice()
        if self.refunded_order_id:
            self.account_move.write({
                "l10n_tw_edi_ecpay_invoice_id": self.refunded_order_id.account_move.l10n_tw_edi_ecpay_invoice_id,
                "l10n_tw_edi_invoice_create_date": self.refunded_order_id.account_move.l10n_tw_edi_invoice_create_date,
            })

            if self.account_move.l10n_tw_edi_ecpay_invoice_id:
                self.env['account.move.send']._generate_and_send_invoices(
                    self.account_move,
                    sending_methods=['manual'],
                    extra_edis={'tw_ecpay_issue_allowance'})
        return res

    def _set_invoice_month(self, data):
        invoice_create_date = datetime.datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
        if invoice_create_date.month % 2 == 0:
            invoice_month = (
                str(invoice_create_date.year - 1911) + "年" + str(invoice_create_date.month - 1) + "-" + str(invoice_create_date.month) + "月"
            )
        else:
            invoice_month = (
                str(invoice_create_date.year - 1911) + "年" + str(invoice_create_date.month) + "-" + str(invoice_create_date.month + 1) + "月"
            )
        return invoice_month

    def get_uniform_invoice(self, name):
        pos_order = self.search([("name", "=", name)], limit=1)
        if pos_order.refunded_order_id:
            invoice = pos_order.refunded_order_id.account_move
        else:
            invoice = self.env["account.move"].search([("ref", "=", pos_order.name)], limit=1)

        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": invoice.l10n_tw_edi_related_number,
        }

        ecpay_api = EcPayAPI(self.company_id)
        response_data = ecpay_api.call_ecpay_api("/GetIssue", json_data)
        json_response = {}
        if response_data.get('RtnCode') != 1:
            error_message = self.env["mail.message"].search([("model", "=", "account.move"), ("res_id", "=", invoice.id), ("message_type", "=", "notification"), ("body", "ilike", "Error")], limit=1).body
            if self.account_move.reversed_entry_id:  # refund invoice
                json_response["error"] = self.env._("No Ecpay invoice to be refunded")
            else:
                json_response["error"] = error_message

        create_date_utc_time = ecpay_api._transfer_time(response_data.get("IIS_Create_Date", False).replace("+", " ")) if response_data.get("IIS_Create_Date", False) else False  # The date return from Ecpay API used "+" instead of " "

        json_response.update({
            "invoice_month": self._set_invoice_month(create_date_utc_time) if create_date_utc_time else False,
            "iis_number": response_data.get("IIS_Number", False),
            "iis_create_date": create_date_utc_time,
            "iis_random_number": response_data.get("IIS_Random_Number", False),
            "iis_tax_amount": response_data.get("IIS_Tax_Amount", False),
            "l10n_tw_edi_invoice_amount": response_data.get("IIS_Sales_Amount", False),
            "iis_identifier": response_data.get("IIS_Identifier", False),
            "iis_carrier_type": response_data.get("IIS_Carrier_Type", False),
            "iis_carrier_num": response_data.get("IIS_Carrier_Num", False),
            "iis_category": response_data.get("IIS_Category", False),
            "l10n_tw_edi_ecpay_seller_identifier": self.env.company.vat,
            "pos_barcode": response_data.get("PosBarCode", False),
            "qrcode_left": response_data.get("QRCode_Left", False),
            "qrcode_right": response_data.get("QRCode_Right", False),
        })
        return json_response

    @api.model
    def l10n_tw_edi_check_mobile_barcode(self, text):
        json_data = {
            "MerchantID": self.env.company.sudo().l10n_tw_edi_ecpay_merchant_id,
            "BarCode": text,
        }

        response_data = EcPayAPI(self.env.company).call_ecpay_api("/CheckBarcode", json_data)
        if int(response_data.get("RtnCode")) == 1 and response_data.get("IsExist") == "Y":
            return True
        else:
            raise UserError(self.env._("Mobile barcode is invalid!"))

    @api.model
    def l10n_tw_edi_check_love_code(self, text):
        json_data = {
            "MerchantID": self.env.company.sudo().l10n_tw_edi_ecpay_merchant_id,
            "LoveCode": text,
        }

        response_data = EcPayAPI(self.env.company).call_ecpay_api("/CheckLoveCode", json_data)
        if int(response_data.get("RtnCode")) == 1 and response_data.get("IsExist") == "Y":
            return True
        else:
            raise UserError(self.env._("Love code is invalid!"))

    @api.model
    def l10n_tw_edi_check_tax_id(self, text):
        json_data = {
            "MerchantID": self.env.company.sudo().l10n_tw_edi_ecpay_merchant_id,
            "UnifiedBusinessNo": text,
        }

        response_data = EcPayAPI(self.env.company).call_ecpay_api("/GetCompanyNameByTaxID", json_data)
        if int(response_data.get("RtnCode")) == 1 and response_data.get("CompanyName"):
            return True
        else:
            raise UserError(self.env._("Tax id is invalid!"))
