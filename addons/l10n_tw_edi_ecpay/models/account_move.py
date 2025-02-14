# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI
from odoo.exceptions import UserError


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
        export_string_translation=False,
    )
    l10n_tw_edi_file = fields.Binary(
        string="Ecpay JSON File",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_tw_edi_ecpay_invoice_id = fields.Char(string="Ecpay Invoice Number", readonly=True, copy=False)
    l10n_tw_edi_related_number = fields.Char(string="Related Number", compute="_compute_l10n_tw_edi_related_number",)
    # False => Not sent yet.
    l10n_tw_edi_state = fields.Selection(
        string="Invoice Status",
        selection=[("invoiced", "Invoiced"), ("valid", "Valid"), ("invalid", "Invalid")],
        copy=False,
        readonly=True,
        tracking=True,
    )
    l10n_tw_edi_love_code = fields.Char(string="Love Code", compute="_compute_love_code", store=True, readonly=False)
    l10n_tw_edi_is_print = fields.Boolean(string="Get Printed Version", compute="_compute_is_print", store=True, readonly=False)
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[
            ("1", "ECpay e-invoice carrier"),
            ("2", "Citizen Digital Certificate"),
            ("3", "Mobile Barcode")
        ],
        copy=False,
        readonly=False,
        compute="_compute_carrier_info",
        store=True,
    )
    l10n_tw_edi_carrier_number = fields.Char(string="Carrier Number", compute="_compute_carrier_info", store=True, readonly=False)
    l10n_tw_edi_invoice_type = fields.Selection(
        string="Invoice Type",
        selection=[
            ("07", "General Invoice"),
            ("08", "Special Invoice")
        ],
        default="07",
        copy=False,
    )
    l10n_tw_edi_clearance_mark = fields.Selection(
        string="Clearance Mark",
        selection=[
            ("1", "NOT via the customs"),
            ("2", "Via the customs")
        ],
        copy=False,
    )
    l10n_tw_edi_zero_tax_rate_reason = fields.Selection(
        string="Zero Tax Rate Reason",
        selection=[
            ("71", "71: No.1 export goods"),
            ("72", "72: No.2 Services related to export sales, or services provided domestically but used abroad"),
            ("73", "73: No.3 Duty-free shops established by law for the sale and transit or departure of passengers"),
            ("74", "74: No.4 Sale of goods or services for operation by the operator of the FREE Trade Zone"),
            ("75", "75: No.5 International transportation. However, foreign transport undertakings operating international transport business in Taiwan shall be limited to those whose countries shall give equal treatment to Taiwan's international transport undertakings or be exempt from similar taxes"),
            ("76", "76: No.6 Ships, aircraft and distant-water fishing vessels for international transportation"),
            ("77", "77: No.7 Goods or repair services used by ships, aircraft and distant-water fishing vessels for sale and international transport"),
            ("78", "78: No.8 The bonded area operator sells goods that are not directly exported by the taxable area operator and the taxable area operator is not exported to the taxation area"),
            ("79", "79: No.9 The bonded area operator sells the goods that the taxable area operator deposits into the bonded warehouse or logistics center managed by the free port area or customs administration for export")
        ],
        copy=False,
    )
    l10n_tw_edi_is_zero_tax_rate = fields.Boolean(string="Is Zero Tax Rate", compute="_compute_is_zero_tax_rate", store=True)
    l10n_tw_edi_invoice_create_date = fields.Datetime(string="Creation Date", readonly=True, copy=False)
    l10n_tw_edi_refund_state = fields.Selection(
        string="Refund State",
        selection=[
            ("to_be_agreed", "To be agreed"),
            ("agreed", "Agreed"),
            ("disagree", "Disagree"),
        ],
        readonly=True,
        copy=False,
    )
    l10n_tw_edi_refund_agreement_type = fields.Selection(
        string="Refund invoice Agreement Type",
        selection=[
            ("offline", "Offline Agreement"),
            ("online", "Online Agreement")
        ],
        default="offline",
        copy=False,
    )
    l10n_tw_edi_allowance_notify_way = fields.Selection(
        string="Allowance Notify Way",
        selection=[
            ("email", "Email"),
            ("phone", "Phone")
        ],
        default="email",
        copy=False,
    )
    l10n_tw_edi_invalidate_reason = fields.Char(string="Invalidate Reason", copy=False)
    l10n_tw_edi_origin_invoice_number_id = fields.Many2one(string="Original Invoice", comodel_name="account.move", readonly=True, copy=False)
    l10n_tw_edi_refund_invoice_number = fields.Char(string="Refund Invoice Number", readonly=True, copy=False)

    @api.depends("name")
    def _compute_l10n_tw_edi_related_number(self):
        for move in self:
            move.l10n_tw_edi_related_number = base64.urlsafe_b64encode(move.name.encode("utf-8")).decode()

    @api.depends("l10n_tw_edi_love_code", "l10n_tw_edi_carrier_type", "partner_id")
    def _compute_is_print(self):
        for move in self:
            if move.l10n_tw_edi_love_code or (move.partner_id.vat and move.l10n_tw_edi_carrier_type in [1, 2]):
                move.l10n_tw_edi_is_print = False

    @api.depends("l10n_tw_edi_is_print", "l10n_tw_edi_carrier_type", "partner_id")
    def _compute_love_code(self):
        for move in self:
            if move.l10n_tw_edi_is_print or move.l10n_tw_edi_carrier_type or move.partner_id.vat:
                move.l10n_tw_edi_love_code = False

    @api.depends("l10n_tw_edi_is_print", "l10n_tw_edi_love_code")
    def _compute_carrier_info(self):
        for move in self:
            if move.l10n_tw_edi_is_print or move.l10n_tw_edi_love_code:
                move.l10n_tw_edi_carrier_type = False
                move.l10n_tw_edi_carrier_number = False

    @api.depends("invoice_line_ids.tax_ids.l10n_tw_edi_tax_type")
    def _compute_is_zero_tax_rate(self):
        for move in self:
            move.l10n_tw_edi_is_zero_tax_rate = move._l10n_tw_edi_compute_tax_type_from_invoice_lines()[2] if move.invoice_line_ids.tax_ids else False

    # ----------------
    # Business methods
    # ----------------
    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        return res | self.l10n_tw_edi_file_id

    # API methods

    # Check the tax type and special tax type on the invoice lines
    def _l10n_tw_edi_check_tax_type_on_invoice_lines(self):
        product_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")

        # Invoive lines without tax or having multiple taxes are not allowed
        if product_lines.filtered(lambda line: not line.tax_ids or len(line.tax_ids) > 1):
            raise UserError(_("Invoive lines without tax or having multiple taxes are not allowed."))

        # Create a set of tax types on invoice lines to check if there are multiple tax types or specific tax type on the invoice lines
        invoice_lines_tax_types = {line.tax_ids[0].l10n_tw_edi_tax_type for line in product_lines if line.tax_ids and line.tax_ids[0].l10n_tw_edi_tax_type}

        if invoice_lines_tax_types:
            # Tax type "4" is a special tax rate, cannot be mixed with other tax types
            if len(invoice_lines_tax_types) > 1 and "4" in invoice_lines_tax_types:
                raise UserError(_("Special tax rate cannot be mixed with other tax types. Please check your tax types on invoice lines."))
            if "4" in invoice_lines_tax_types and len({line.tax_ids[0].l10n_tw_edi_special_tax_type for line in product_lines if line.tax_ids and line.tax_ids[0].l10n_tw_edi_tax_type == "4" and line.tax_ids[0].l10n_tw_edi_special_tax_type}) > 1:
                raise UserError(_("Special tax type cannot be mixed with other special tax types. Please check your special tax types on invoice lines."))

            if "2" in invoice_lines_tax_types and "3" in invoice_lines_tax_types:
                raise UserError(_("Tax type 2 (Zero tax rate) and type 3 (Duty free) cannot be used together. Please check your tax types on invoice lines."))
        else:
            raise UserError(_("Please fill in the tax on the invoice lines and select the Ecpay tax type for taxes."))

    # Calculate and return the tax type, special tax type and is zero tax rate included based on the taxes on invoice lines
    def _l10n_tw_edi_compute_tax_type_from_invoice_lines(self):
        product_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        # Create a set of tax types on invoice lines to check if there are multiple tax types or specific tax type on the invoice lines
        invoice_lines_tax_types = {line.tax_ids[0].l10n_tw_edi_tax_type for line in product_lines if line.tax_ids and line.tax_ids[0].l10n_tw_edi_tax_type}

        if invoice_lines_tax_types:
            if len(invoice_lines_tax_types) > 1:  # mixed tax types
                return ["9", "0", "2" in invoice_lines_tax_types]
            elif "4" in invoice_lines_tax_types:  # special tax rate
                return ["4", product_lines[0].tax_ids.l10n_tw_edi_special_tax_type, False]
            elif "3" in invoice_lines_tax_types:
                return ["3", "8", False]
            else:
                return [list(invoice_lines_tax_types)[0], "0", "2" in invoice_lines_tax_types]
        return False, False, False

    # Convert currency to TWD if the currency is not TWD
    def _l10n_tw_edi_convert_currency_to_twd(self, amount):
        if self.currency_id.name == "TWD":
            return amount
        return self.currency_id._convert(amount, self.env.ref("base.TWD"), self.company_id, fields.Date.context_today(self))

    def _l10n_tw_edi_prepare_item_list(self, json_data):
        item_list = []
        for line in self.invoice_line_ids.filtered(lambda line: line.display_type == "product"):
            price_total = self._l10n_tw_edi_convert_currency_to_twd(line.price_total)
            item_list.append(
                {
                    "ItemSeq": line.sequence,
                    "ItemName": line.product_id.name[:100],
                    "ItemCount": int(line.quantity),
                    "ItemWord": line.product_uom_id.name[:6],
                    "ItemPrice": int(price_total / line.quantity),
                    "ItemTaxType": line.tax_ids.l10n_tw_edi_tax_type if self._l10n_tw_edi_compute_tax_type_from_invoice_lines()[0] == "9" else "",
                    "ItemAmount": int(price_total),
                }
            )
        json_data["Items"] = item_list

    def _l10n_tw_edi_generate_invoice_json(self):
        if not self.company_id.l10n_tw_edi_ecpay_merchant_id:
            raise UserError(_("Please fill in the ECpay API information in the Setting!"))

        if (self.l10n_tw_edi_is_print or self.partner_id.vat) and not self.partner_id.contact_address:
            raise UserError(_("Please fill in the customer address for printing Ecpay invoice."))

        if not self.partner_id.email and not self.partner_id.phone:
            raise UserError(_("Please fill in the customer email or phone number for Ecpay invoice creation."))

        self._l10n_tw_edi_check_tax_type_on_invoice_lines()

        tax_type, special_tax_type, is_zero_tax_rate = self._l10n_tw_edi_compute_tax_type_from_invoice_lines()

        if self.l10n_tw_edi_invoice_type == "07" and tax_type not in ["1", "2", "3", "9"]:
            raise UserError(_("Invoice type 07 must be used with tax type 1, 2 or 9. Please check the tax type on the invoice lines."))

        if self.l10n_tw_edi_invoice_type == "08" and tax_type not in ["3", "4"]:
            raise UserError(_("Invoice type 08 must be used with tax type 3 or 4. Please check the tax type on the invoice lines."))

        json_data = {
            "MerchantID": self.company_id.l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": self.l10n_tw_edi_related_number,
            "CustomerIdentifier": self.partner_id.vat or "",
            "CustomerName": self.commercial_partner_id.name if self.partner_id.vat else self.partner_id.name,
            "CustomerAddr": self.partner_id.contact_address,
            "CustomerEmail": self.partner_id.email or "",
            "CustomerPhone": self.partner_id.phone or "",
            "Print": "1" if self.l10n_tw_edi_is_print or self.partner_id.vat else "0",
            "Donation": "1" if self.l10n_tw_edi_love_code else "0",
            "LoveCode": self.l10n_tw_edi_love_code or "",
            "CarrierType": self.l10n_tw_edi_carrier_type or "",
            "CarrierNum": self.l10n_tw_edi_carrier_number if self.l10n_tw_edi_carrier_type in ["2", "3"] else "",
            "InvType": self.l10n_tw_edi_invoice_type,
            "TaxType": tax_type,
            "SpecialTaxType": special_tax_type,
            "vat": "0" if tax_type == "3" else "1",
            "SalesAmount": int(self._l10n_tw_edi_convert_currency_to_twd(self.amount_total)),
            "InvoiceRemark": self.ref,
        }

        if is_zero_tax_rate:
            if not self.l10n_tw_edi_clearance_mark and not self.l10n_tw_edi_zero_tax_rate_reason:
                raise UserError(_(" Clearance mark and Zero tax rate reason is required for zero tax rate invoice."))
            json_data["ClearanceMark"] = self.l10n_tw_edi_clearance_mark,
            json_data["ZeroTaxRateReason"] = self.l10n_tw_edi_zero_tax_rate_reason,

        self._l10n_tw_edi_prepare_item_list(json_data)

        return json_data

    def _l10n_tw_edi_send(self, json_content):
        """
        Issuing an e-invoice by calling the Ecpay API and update the invoicing result in Odoo
        """
        self.ensure_one()
        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)

        ecpay_api = EcPayAPI(self.company_id)
        response_data = ecpay_api.call_ecpay_api("/Issue", json_content)
        if response_data.get("RtnCode") != 1:
            return [_("Invoice %(name)s Error: %(error_message)s", name=self.name, error_message=response_data.get("RtnMsg"))]
        self.write({
            "l10n_tw_edi_ecpay_invoice_id": response_data.get("InvoiceNo"),
            "l10n_tw_edi_invoice_create_date": ecpay_api._transfer_time(response_data.get("InvoiceDate").replace("+", " ")),  # The date return from Ecpay API used "+" instead of " "
            "l10n_tw_edi_state": "invoiced",
        })
        self._message_log(
            body=_("The invoice has been successfully sent to Ecpay with Ecpay invoice number %(invoice_number)s.", invoice_number=response_data.get("InvoiceNo")),
        )

    def _l10n_tw_edi_update_ecpay_invoice_info(self):
        """
        Searching the e-invoice information from Ecpay API and update the invoice information in Odoo
        """
        self.ensure_one()
        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)

        if not self.l10n_tw_edi_related_number:
            raise UserError(_("The invoice: %(invoice_name)s has no related number", invoice_id=self.name))

        json_data = {
            "MerchantID": self.company_id.l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": self.l10n_tw_edi_related_number,
        }

        response_data = EcPayAPI(self.company_id).call_ecpay_api("/GetIssue", json_data)
        if response_data.get("RtnCode") != 1:
            return [_("Invoice %(name)s Error: %(error_message)s", name=self.name, error_message=response_data.get("RtnMsg"))]

        self.l10n_tw_edi_state = "valid" if response_data.get("IIS_Invalid_Status") == "0" else "invalid"

    def _l10n_tw_edi_run_invoice_invalid(self):
        """
        Cancelling the e-invoice by calling the Ecpay API and update the invoice information in Odoo
        """
        self.ensure_one()
        if not self.l10n_tw_edi_ecpay_invoice_id:
            raise UserError(_("You cannot invalidate an invoice that was not sent to Ecpay."))
        if self.l10n_tw_edi_state == "invalid":
            raise UserError(_("The invoice: %(invoice_id)s has already been invalidated", invoice_id=self.l10n_tw_edi_ecpay_invoice_id))

        json_data = {
            "MerchantID": self.company_id.l10n_tw_edi_ecpay_merchant_id,
            "InvoiceNo": self.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Reason": self.l10n_tw_edi_invalidate_reason
        }

        response_data = EcPayAPI(self.company_id).call_ecpay_api("/Invalid", json_data)

        if response_data.get("RtnCode") != 1:
            raise UserError(_("Fail to invalidate invoice. Error message: %(error_message)s", error_message=response_data.get("RtnMsg")))

        # update the invoice information in Odoo
        self._l10n_tw_edi_update_ecpay_invoice_info()

    def l10n_tw_edi_issue_allowance(self):
        """
        Issuing an allowance by calling the Ecpay API and update the refund invoice information in Odoo
        Two methods to issue the allowance
        1. Endpoint: /Allowance
            General allowance, which requires merchants or sellers to get the agreement from the customer first (not by using ECPay system)
            and then to send an API request to ECPay to issue an allowance.
        2. Endpoint: /AllowanceByCollegiate
            Sending an API request to ECPay and ECPay will send an e-mail notification with a link to the customer to get his/her agreement
            ONce the customer clicks the link, an allowance will be issued instantly
        """
        self.ensure_one()
        if not self.l10n_tw_edi_ecpay_invoice_id:
            raise UserError(_("You cannot issue an allowance for an invoice that was not sent to Ecpay. Invoice number: %(invoice_number)s", invoice_number=self.name))

        json_data = {}

        if self.l10n_tw_edi_refund_agreement_type == "online":
            if not self.partner_id.email:
                raise UserError(_("Customer email is needed for notification"))
            query_param = "/AllowanceByCollegiate"
            json_data["ReturnURL"] = urljoin(self.get_base_url(), f"/invoice/ecpay/agreed_invoice_allowance/{self.id}?access_token={self._portal_ensure_token()}")
        else:
            query_param = "/Allowance"

        if self.l10n_tw_edi_allowance_notify_way == "email" and self.partner_id.email:
            json_data["AllowanceNotify"] = "E"
            json_data["NotifyMail"] = self.partner_id.email
        elif self.l10n_tw_edi_allowance_notify_way == "phone" and self.partner_id.phone:
            json_data["AllowanceNotify"] = "S"
            json_data["NotifyPhone"] = self.partner_id.phone.replace("+", "").replace(" ", "")
        else:
            raise UserError(_("Customer %(notify_way)s is needed for notification", notify_way=self.l10n_tw_edi_allowance_notify_way))

        json_data.update({
            "MerchantID": self.company_id.l10n_tw_edi_ecpay_merchant_id,
            "InvoiceNo": self.l10n_tw_edi_ecpay_invoice_id,
            "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "AllowanceAmount": int(self._l10n_tw_edi_convert_currency_to_twd(self.amount_total)),
        })
        self._l10n_tw_edi_prepare_item_list(json_data)

        response_data = EcPayAPI(self.company_id).call_ecpay_api(query_param, json_data)

        if response_data.get("RtnCode") != 1:
            raise UserError(_("Fail to issue allowance for ECpay invoice. Error message: %(error_message)s", error_message=response_data.get("RtnMsg")))

        self.write({
            "l10n_tw_edi_refund_invoice_number": response_data.get("IA_Allow_No"),
            "l10n_tw_edi_refund_state": "to_be_agreed" if self.l10n_tw_edi_refund_agreement_type == "online" else "agreed",
        })
