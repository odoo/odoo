from odoo import _, fields, models
import datetime
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI


class PoSOrder(models.Model):
    _inherit = "pos.order"

    ecpay_is_print = fields.Boolean(string="Print")
    ecpay_is_donate = fields.Boolean(string="Donate")
    ecpay_love_code = fields.Char(string="Love Code")
    ecpay_customer_identifier = fields.Char(string="Tax ID Number")
    ecpay_customer_name = fields.Char(string="Customer Name")
    ecpay_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[("1", "ECpay e-invoice carrier"), ("2", "Citizen Digital Certificate"), ("3", "Mobile Barcode")],
    )
    ecpay_carrier_number = fields.Char(string="Carrier Number")
    ecpay_customer_address = fields.Char(string="Customer Address")
    ecpay_customer_email = fields.Char(string="Customer Email")
    ecpay_customer_phone = fields.Char(string="Customer Phone")

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

    def _transfer_time(self, time_before):
        time_after = (
            datetime.datetime.strptime(time_before, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=8)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return time_after

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        vals.update({
            'l10n_tw_edi_is_print': self.ecpay_is_print,
            'l10n_tw_edi_is_donate': self.ecpay_is_donate,
            'l10n_tw_edi_love_code': self.ecpay_love_code,
            'l10n_tw_edi_customer_identifier': self.ecpay_customer_identifier,
            'l10n_tw_edi_customer_name': self.ecpay_customer_name,
            'l10n_tw_edi_carrier_type': self.ecpay_carrier_type,
            'l10n_tw_edi_carrier_number': self.ecpay_carrier_number,
            'l10n_tw_edi_customer_address': self.ecpay_customer_address,
            'l10n_tw_edi_customer_email': self.ecpay_customer_email,
            'l10n_tw_edi_customer_phone': self.ecpay_customer_phone,
        })
        return vals

    def _generate_pos_order_invoice(self):
        res = super()._generate_pos_order_invoice()
        if self.refunded_order_id:
            self.account_move.l10n_tw_edi_origin_invoice_number = self.refunded_order_id.account_move
            self.account_move.l10n_tw_edi_ecpay_invoice_id = self.refunded_order_id.account_move.l10n_tw_edi_ecpay_invoice_id
            self.account_move.l10n_tw_edi_invoice_create_date = self.refunded_order_id.account_move.l10n_tw_edi_invoice_create_date
            if self.account_move.l10n_tw_edi_ecpay_invoice_id:
                self.account_move.l10n_tw_edi_run_refund()
                self.account_move.l10n_tw_edi_is_refund = True
        return res

    def get_uniform_invoice(self, name):
        pos_order = self.search([("name", "=", name)], limit=1)
        if pos_order.refunded_order_id:
            invoice = pos_order.refunded_order_id.account_move
        else:
            invoice = self.env["account.move"].search([("ref", "=", pos_order.name)], limit=1)

        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "RelateNumber": invoice.l10n_tw_edi_related_number,
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/GetIssue", json_data)
        json_response = {}
        if response_data.get('RtnCode') != 1:
            error_message = self.env["mail.message"].search([("model", "=", "account.move"), ("res_id", "=", invoice.id), ("message_type", "=", "notification")], limit=1).body
            if self.account_move.l10n_tw_edi_origin_invoice_number:  # refund invoice
                json_response.update({"error": _("No Ecpay invoice to be refunded")})
            else:
                json_response.update({"error": error_message})

        create_date_utc_time = self._transfer_time(response_data.get("IIS_Create_Date").replace("+", " ")) if response_data.get("IIS_Create_Date") else False

        json_response.update({
            "invoice_month": self._set_invoice_month(create_date_utc_time) if create_date_utc_time else False,
            "IIS_Number": response_data.get("IIS_Number", False),
            "IIS_Create_Date": create_date_utc_time,
            "IIS_Random_Number": response_data.get("IIS_Random_Number", False),
            "IIS_Tax_Amount": response_data.get("IIS_Tax_Amount", False),
            "l10n_tw_edi_invoice_amount": response_data.get("IIS_Sales_Amount", False),
            "IIS_Identifier": response_data.get("IIS_Identifier", False),
            "IIS_Carrier_Type": response_data.get("IIS_Carrier_Type", False),
            "IIS_Carrier_Num": response_data.get("IIS_Carrier_Num", False),
            "IIS_Category": response_data.get("IIS_Category", False),
            "l10n_tw_edi_ecpay_seller_identifier": self.env.company.l10n_tw_edi_ecpay_seller_identifier,
            "PosBarCode": response_data.get("PosBarCode", False),
            "QRCode_Left": response_data.get("QRCode_Left", False),
            "QRCode_Right": response_data.get("QRCode_Right", False),
        })
        return json_response
