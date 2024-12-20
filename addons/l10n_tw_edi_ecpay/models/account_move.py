# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_tw_edi_file_id = fields.Many2one(
        comodel_name="ir.attachment",
        compute=lambda self: self._compute_linked_attachment_id("l10n_tw_edi_file_id", "l10n_tw_edi_file"),
        depends=["l10n_tw_edi_file"],
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_tw_edi_file = fields.Binary(
        string="Ecpay JSON File",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_tw_edi_ecpay_invoice_id = fields.Char(string="Ecpay Invoice Number", readonly=True, copy=False)
    l10n_tw_edi_related_number = fields.Char("Ralated Number")
    # False => Not sent yet.
    l10n_tw_edi_state = fields.Selection(
        selection=[("invoiced", "Invoiced"), ("valid", "Valid"), ("invalid", "Invalid")],
        string="Invoice Status",
        copy=False,
        readonly=True,
        tracking=True,
        export_string_translation=False,
    )
    l10n_tw_edi_ecpay_tax_type = fields.Selection(
        selection=[("1", "tax included"), ("0", "untax")],
        string="With Tax",
        default="1",
        copy=False,
    )
    l10n_tw_edi_is_donate = fields.Boolean(string="Donate", copy=False, compute="_compute_is_donate", store=True, readonly=False)
    l10n_tw_edi_love_code = fields.Char(string="Love Code", copy=False, compute="_compute_is_donate", store=True, readonly=False)
    l10n_tw_edi_is_print = fields.Boolean(string="Get Printed Version", copy=False, compute="_compute_is_print", store=True, readonly=False)
    l10n_tw_edi_carrier_type = fields.Selection(
        selection=[("1", "ECpay e-invoice carrier"), ("2", "Citizen Digital Certificate"), ("3", "Mobile Barcode")],
        string="Carrier Type",
        copy=False,
        compute="_compute_carrier_info",
        store=True,
        readonly=False)
    l10n_tw_edi_carrier_number = fields.Char(string="Carrier Number", copy=False, compute="_compute_carrier_info", store=True, readonly=False)
    l10n_tw_edi_customer_identifier = fields.Char(string="Tax ID Number", copy=False)
    l10n_tw_edi_customer_name = fields.Char(string="Customer Name", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_address = fields.Char(string="Customer shipping address", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_email = fields.Char(string="Customer Email", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_customer_phone = fields.Char(string="Customer Phone", compute="_compute_customer_info", store=True, readonly=False)
    l10n_tw_edi_invoice_amount = fields.Float(string="Invoice Amount", readonly=True, copy=False)
    l10n_tw_edi_invoice_valid_status = fields.Selection(string="Valid Status", selection=[("1", "Abolish"), ("0", "Valid")], readonly=True, copy=False)
    l10n_tw_edi_invoice_issue_status = fields.Selection(string="Issue Status", selection=[("1", "Invoice issued"), ("0", "Invoice cancelled")], readonly=True, copy=False)
    l10n_tw_edi_invoice_shop_custom_number = fields.Char(string="Cooperative Shop Custom Number", readonly=True, copy=False)
    l10n_tw_edi_invoice_create_date = fields.Datetime(string="Creation Date", readonly=True, copy=False)
    l10n_tw_edi_is_refund = fields.Boolean(string="Refund", readonly=True, copy=False)
    l10n_tw_edi_refund_finish = fields.Boolean(string="Refund Finish", readonly=True, copy=False)
    l10n_tw_edi_refund_state = fields.Selection(
        selection=[
            ("draft", "draft"),
            ("to be agreed", "To be agreed"),
            ("agreed", "Agreed"),
            ("disagree", "Disagree"),
        ],
        string="Refund State",
        default="draft",
        readonly=True,
        copy=False,
    )
    l10n_tw_edi_refund_agreement_type = fields.Selection(
        [("offline", "Offline Agreement"), ("online", "Online Agreement")],
        default="offline",
        string="Refund invoice Agreement Type",
        required=True,
        copy=False,
    )
    l10n_tw_edi_origin_invoice_number = fields.Many2one('account.move', string="Original Invoice", readonly=True, copy=False)
    l10n_tw_edi_refund_invoice_number = fields.Char(string="Refund Invoice Number", readonly=True, copy=False)
    l10n_tw_edi_remain_refundable_amount = fields.Float(string="Remain refundable amount", readonly=True, copy=False)
    l10n_tw_edi_ecpay_invoice_code = fields.Char(string="ECpay invoice code", copy=False)

    @api.depends('l10n_tw_edi_is_donate', 'l10n_tw_edi_carrier_type')
    def _compute_is_print(self):
        for move in self:
            if move.l10n_tw_edi_is_donate or move.l10n_tw_edi_carrier_type:
                move.l10n_tw_edi_is_print = False

    @api.depends('l10n_tw_edi_is_print', 'l10n_tw_edi_carrier_type')
    def _compute_is_donate(self):
        for move in self:
            if move.l10n_tw_edi_is_print or move.l10n_tw_edi_carrier_type:
                move.l10n_tw_edi_is_donate = False
                move.l10n_tw_edi_love_code = False

    @api.depends('l10n_tw_edi_is_print', 'l10n_tw_edi_is_donate')
    def _compute_carrier_info(self):
        for move in self:
            if move.l10n_tw_edi_is_print or move.l10n_tw_edi_is_donate:
                move.l10n_tw_edi_carrier_type = False
                move.l10n_tw_edi_carrier_number = False

    @api.depends('partner_id')
    def _compute_customer_info(self):
        for move in self:
            move.l10n_tw_edi_customer_name = move.partner_id.name
            move.l10n_tw_edi_customer_address = move.partner_id.contact_address
            move.l10n_tw_edi_customer_email = move.partner_id.email
            move.l10n_tw_edi_customer_phone = move.partner_id.phone

    # ----------------
    # Business methods
    # ----------------

    # API methods

    def _l10n_tw_edi_prepare_item_list(self):
        res = []
        for line in self.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and not line._get_downpayment_lines()):
            taxable = line.tax_ids.filtered(lambda t: t.amount >= 5.0)
            item_price = round(line.price_unit, 2)
            res.append(
                {
                    "ItemSeq": line.sequence,
                    "ItemName": line.product_id.name[:100],
                    "ItemCount": int(line.quantity),
                    "ItemWord": line.product_uom_id.name[:6],
                    "ItemPrice": item_price,
                    "ItemTaxType": "1" if len(taxable.ids) >= 1 else "3",
                    "ItemAmount": round(line.price_total, 2),
                }
            )
        return res

    def _l10n_tw_edi_generate_invoice_json(self):
        if not self.env.company.l10n_tw_edi_ecpay_merchant_id:
            raise UserError(_("Please fill in the ECpay API information in the Setting!"))

        # prepare json data
        self.l10n_tw_edi_related_number = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode()
        json_data = {
            "MerchantID": self.env.company.l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": self.l10n_tw_edi_related_number,
            "CustomerIdentifier": self.l10n_tw_edi_customer_identifier or "",
            "CustomerName": self.l10n_tw_edi_customer_name,
            "CustomerAddr": self.l10n_tw_edi_customer_address,
            "CustomerPhone": self.l10n_tw_edi_customer_phone or '',
            "CustomerEmail": self.l10n_tw_edi_customer_email or '',
            "ClearanceMark": "",
            "Print": str(int(self.l10n_tw_edi_is_print or self.l10n_tw_edi_customer_identifier)),
            "Donation": str(int(self.l10n_tw_edi_is_donate)),
            "TaxType": "1",
            "SalesAmount": int(self.amount_total),
            "InvoiceRemark": "Odoo",
            "InvType": "07",
            "vat": self.l10n_tw_edi_ecpay_tax_type,
            "CarrierType": self.l10n_tw_edi_carrier_type or "",
            "CarrierNum": self.l10n_tw_edi_carrier_number if self.l10n_tw_edi_carrier_type in ["2", "3"] else "",
            "Items": self._l10n_tw_edi_prepare_item_list()
        }
        if self.l10n_tw_edi_is_donate:
            json_data.update({"LoveCode": self.l10n_tw_edi_love_code})
        return json_data

    def _transfer_time(self, time_before):
        time_after = (
            datetime.datetime.strptime(time_before, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=8)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return time_after

    def _l10n_tw_edi_send(self, json_content):
        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()
        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)
        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/Issue", json_content)
        if response_data.get("RtnCode") != 1:
            return [_(f"Invoice {self.name} Error: {response_data.get('RtnMsg')}")]
        self.l10n_tw_edi_ecpay_invoice_id = response_data.get("InvoiceNo")
        self.l10n_tw_edi_invoice_create_date = self._transfer_time(response_data.get("InvoiceDate").replace("+", " "))
        self.l10n_tw_edi_state = "invoiced"
        self._message_log(
            body=_("The invoice has been successfully sent to Ecpay with Ecpay invoice number '%s'.", response_data.get('InvoiceNo')),
        )

    def _l10n_tw_edi_fetch_ecpay_invoice(self):
        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()
        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)
        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "RelateNumber": self.l10n_tw_edi_related_number,
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/GetIssue", json_data)
        if response_data.get('RtnCode') != 1:
            return [_(f"Invoice {self.name} Error: {response_data.get('RtnMsg')}")]
        self.l10n_tw_edi_invoice_amount = response_data.get("IIS_Sales_Amount")
        self.l10n_tw_edi_invoice_valid_status = response_data.get("IIS_Invalid_Status")
        self.l10n_tw_edi_invoice_issue_status = response_data.get("IIS_Issue_Status")
        self.l10n_tw_edi_invoice_shop_custom_number = response_data.get("IIS_Relate_Number")
        self.l10n_tw_edi_remain_refundable_amount = response_data.get("IIS_Remain_Allowance_Amt")
        self.l10n_tw_edi_state = "valid"

    def _l10n_tw_edi_run_invoice_invalid(self):
        if self.l10n_tw_edi_ecpay_invoice_id:
            if self.l10n_tw_edi_invoice_valid_status == "1":
                raise UserError(_(f"The following invoice: {self.l10n_tw_edi_ecpay_invoice_id} is abolished"))
        else:
            raise UserError(_("Cannot find related invoice"))

        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()

        # prepare json data
        json_data = {
            "MerchantID": merchant_id,
            "InvoiceNo": self.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Reason": self.name
        }

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + "/Invalid", json_data)

        if response_data.get("RtnCode") != 1:
            raise UserError(_("Fail to abolish invoice. Error message: " + response_data.get("RtnMsg")))

        # update the ecpay invoice information in Odoo
        self._l10n_tw_edi_fetch_ecpay_invoice()

    def l10n_tw_edi_run_refund(self):
        if not self.l10n_tw_edi_ecpay_invoice_id:
            raise UserError(_("Cannot find the Ecpay invoice"))

        json_data = {}

        if self.l10n_tw_edi_refund_agreement_type == "online":
            if not self.partner_id.email:
                raise UserError(_("Customer email is needed for notification"))
            query_param = "/AllowanceByCollegiate"
            base_url = self.env.company.l10n_tw_edi_ecpay_allowance_domain if self.env.company.l10n_tw_edi_ecpay_allowance_domain else self.env["ir.config_parameter"].sudo().get_param("web.base.url")
            refund_url = f"/invoice/ecpay/agreed_invoice_allowance/{self.id}?access_token={self._portal_ensure_token()}"
            json_data.update({"ReturnURL": base_url + refund_url})
        else:
            query_param = "/Allowance"

        request_url, merchant_id, hashkey, hashIV = self.env.company._l10n_tw_edi_prepare_api_param()

        if self.partner_id.email:
            json_data.update({
                "AllowanceNotify": "E",
            })
        elif self.partner_id.phone:
            json_data.update({
                "AllowanceNotify": "S",
            })
        else:
            raise UserError(_("Customer email or phone is needed for notification"))
        json_data.update({
            "MerchantID": merchant_id,
            "InvoiceNo": self.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "NotifyMail": self.partner_id.email if self.partner_id.email else "",
            "NotifyPhone": self.partner_id.phone.replace("+", "").replace(" ", "") if self.partner_id.phone else "",
            "Items": self._l10n_tw_edi_prepare_item_list(),
            "AllowanceAmount": self.amount_total,
        })

        # prepare EcPayAPI class
        response_data = EcPayAPI(hashkey, hashIV, merchant_id).call_ecpay_api(request_url + query_param, json_data)

        if response_data.get("RtnCode") != 1:
            raise UserError(_("Refund ecpay invoice creation fail. Error message: " + response_data.get("RtnMsg")))

        self.l10n_tw_edi_refund_invoice_number = response_data.get("IA_Allow_No")
        self.l10n_tw_edi_origin_invoice_number.l10n_tw_edi_remain_refundable_amount = response_data.get("IA_Remain_Allowance_Amt")
        self.l10n_tw_edi_refund_finish = True

        if self.l10n_tw_edi_refund_agreement_type == "online":
            self.l10n_tw_edi_refund_state = "to be agreed"
        else:
            self.l10n_tw_edi_refund_state = "agreed"
