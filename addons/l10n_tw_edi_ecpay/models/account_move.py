# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from decimal import Decimal, ROUND_HALF_UP
import re
from urllib.parse import urljoin

from odoo import api, fields, models
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
    l10n_tw_edi_related_number = fields.Char(
        string="Related Number",
        copy=False,
        readonly=True,
        store=True,
    )
    # False => Not sent yet.
    l10n_tw_edi_state = fields.Selection(
        string="Invoice Status",
        selection=[
            ("invoiced", "Invoiced"),
            ("valid", "Valid"),
            ("invalid", "Invalid"),
        ],
        copy=False,
        readonly=True,
        tracking=True,
    )
    l10n_tw_edi_love_code = fields.Char(string="Love Code", compute="_compute_love_code", store=True, readonly=False)
    l10n_tw_edi_is_print = fields.Boolean(
        string="Get Printed Version",
        compute="_compute_is_print",
        store=True,
        readonly=False,
    )
    l10n_tw_edi_carrier_type = fields.Selection(
        string="Carrier Type",
        selection=[
            ("1", "ECpay e-invoice carrier"),
            ("2", "Citizen Digital Certificate"),
            ("3", "Mobile Barcode"),
            ("4", "EasyCard"),
            ("5", "iPass"),
        ],
        copy=False,
        readonly=False,
        compute="_compute_carrier_info",
        store=True,
        help="""
    - Citizen Digital Certificate: The carrier number format is 2 capital letters following 14 digits.
    - Mobile Barcode: The carrier number format is / following 7 alphanumeric or +-. string.
    - EasyCard or iPass: The carrier number is the card hidden code, the carrier number 2 is the card visible code.
        """
    )
    l10n_tw_edi_carrier_number = fields.Char(
        string="Carrier Number",
        compute="_compute_carrier_info",
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_tw_edi_carrier_number_2 = fields.Char(
        string="Carrier Number 2",
        compute="_compute_carrier_info",
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_tw_edi_invoice_type = fields.Selection(
        string="Ecpay Invoice Type",
        selection=[
            ("07", "General Invoice"),
            ("08", "Special Invoice"),
        ],
        compute="_compute_l10n_tw_edi_tax_info",
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_tw_edi_clearance_mark = fields.Selection(
        string="Clearance Mark",
        selection=[
            ("1", "NOT via the customs"),
            ("2", "Via the customs"),
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
            ("75", "75: No.5 International transportation. However, foreign transport undertakings operating "
                "international transport business in Taiwan shall be limited to those whose countries shall give equal "
                "treatment to Taiwan's international transport undertakings or be exempt from similar taxes"),
            ("76", "76: No.6 Ships, aircraft and distant-water fishing vessels for international transportation"),
            ("77", "77: No.7 Goods or repair services used by ships, aircraft and distant-water fishing vessels for "
                "sale and international transport"),
            ("78", "78: No.8 The bonded area operator sells goods that are not directly exported by the taxable"
                " area operator and the taxable area operator is not exported to the taxation area"),
            ("79", "79: No.9 The bonded area operator sells the goods that the taxable area operator deposits into the "
                "bonded warehouse or logistics center managed by the free port area or customs administration for export"),
        ],
        copy=False,
    )
    l10n_tw_edi_is_zero_tax_rate = fields.Boolean(
        string="Is Zero Tax Rate",
        compute="_compute_l10n_tw_edi_tax_info",
        store=True,
        copy=False,
    )
    l10n_tw_edi_invoice_create_date = fields.Datetime(string="Creation Date", readonly=True, copy=False)
    l10n_tw_edi_refund_state = fields.Selection(
        string="Refund State",
        selection=[
            ("to_be_agreed", "To be agreed"),
            ("agreed", "Agreed"),
            ("disagreed", "Disagreed"),
        ],
        readonly=True,
        copy=False,
    )
    l10n_tw_edi_refund_agreement_type = fields.Selection(
        string="Refund invoice Agreement Type",
        selection=[
            ("offline", "Offline Agreement"),
            ("online", "Online Agreement"),
        ],
        default="offline",
        copy=False,
    )
    l10n_tw_edi_allowance_notify_way = fields.Selection(
        string="Allowance Notify Way",
        selection=[
            ("email", "Email"),
            ("phone", "Phone"),
        ],
        default="email",
        copy=False,
    )
    l10n_tw_edi_invalidate_reason = fields.Char(string="Invalidate Reason", readonly=True, copy=False)
    l10n_tw_edi_refund_invoice_number = fields.Char(string="Refund Invoice Number", readonly=True, copy=False)
    l10n_tw_edi_is_b2b = fields.Boolean(string="Is B2B", compute="_compute_l10n_tw_edi_is_b2b")

    @api.depends("l10n_tw_edi_state")
    def _compute_need_cancel_request(self):
        # EXTENDS 'account'
        super()._compute_need_cancel_request()

    @api.depends("l10n_tw_edi_state", "l10n_tw_edi_refund_state")
    def _compute_show_reset_to_draft_button(self):
        # EXTEND 'account'
        super()._compute_show_reset_to_draft_button()
        if self.move_type == "out_invoice":
            self.filtered(lambda m: m.l10n_tw_edi_state and m.l10n_tw_edi_state != "invalid").show_reset_to_draft_button = False
        elif self.move_type == "out_refund":
            self.filtered(lambda m: m.l10n_tw_edi_refund_state).show_reset_to_draft_button = False

    def _need_cancel_request(self):
        # EXTENDS 'account'
        return super()._need_cancel_request() or self.l10n_tw_edi_state in ["invoiced", "valid"]

    def button_request_cancel(self):
        # EXTENDS 'account'
        if self._need_cancel_request() and self.l10n_tw_edi_state in ["invoiced", "valid"]:
            return {
                "name": self.env._("Cancel Ecpay Invoice"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "l10n_tw_edi.invoice.cancel",
                "target": "new",
                "context": {
                    "default_invoice_id": self.id,
                },
            }
        return super().button_request_cancel()

    def button_draft(self):
        # EXTENDS 'account'
        invoices_to_reset = self.filtered(
            lambda i: (i.state == "cancel" and i.l10n_tw_edi_state == "invalid")
        )
        res = super().button_draft()

        invoices_to_reset.write({
            "l10n_tw_edi_related_number": False,
            "l10n_tw_edi_state": False,
            "l10n_tw_edi_ecpay_invoice_id": False,
            "l10n_tw_edi_invoice_create_date": False,
            "l10n_tw_edi_invalidate_reason": False,
        })
        invoices_to_reset.l10n_tw_edi_file_id.unlink()
        return res

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
                move.l10n_tw_edi_carrier_number_2 = False

    @api.depends("invoice_line_ids.tax_ids.l10n_tw_edi_tax_type")
    def _compute_l10n_tw_edi_tax_info(self):
        for move in self:
            tax_type, special_tax_type, is_zero_tax_rate = move._l10n_tw_edi_compute_tax_type_from_invoice_lines()
            if tax_type == "3":
                move.l10n_tw_edi_invoice_type = "07" if not special_tax_type else "08"
            else:
                move.l10n_tw_edi_invoice_type = "07" if tax_type != "4" else "08"
            move.l10n_tw_edi_is_zero_tax_rate = is_zero_tax_rate if move.invoice_line_ids.tax_ids else False

    @api.depends("partner_id.parent_id", "partner_id.company_type")
    def _compute_l10n_tw_edi_is_b2b(self):
        for rec in self:
            rec.l10n_tw_edi_is_b2b = (rec.partner_id.parent_id and rec.partner_id.parent_id.company_type == "company") or rec.partner_id.company_type == "company"

    # ----------------
    # Business methods
    # ----------------
    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        return res | self.l10n_tw_edi_file_id

    # API methods
    def _l10n_tw_edi_rounding(self, num):
        """
        Round the number to two decimal places using ROUND_HALF_UP (3.115 -> 3.12, 3.114 -> 3.11)
        """
        return float(Decimal(str(num)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def _l10n_tw_edi_check_tax_type_on_invoice_lines(self):
        """
        Check the tax type and special tax type on the invoice lines
        """
        self.ensure_one()
        product_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        errors = []
        # Invoice lines without tax or having multiple taxes are not allowed
        if product_lines.filtered(lambda line: not line.tax_ids or len(line.tax_ids) > 1):
            errors.append(self.env._("Invoice lines without taxes or more than one tax are not allowed."))

        if len(set(product_lines.tax_ids.mapped('price_include'))) > 1:
            errors.append(self.env._("Invoice lines with different tax include/exclude are not allowed."))

        # Create a set of tax types on invoice lines to check if there are multiple tax types or specific tax type on the invoice lines
        invoice_lines_tax_types = set(product_lines.tax_ids.mapped('l10n_tw_edi_tax_type'))

        if invoice_lines_tax_types:
            # Tax type "4" is a special tax rate, cannot be mixed with other tax types
            if "4" in invoice_lines_tax_types and len(invoice_lines_tax_types) > 1:
                errors.append(self.env._(
                    "Special tax type cannot be mixed with other tax types."
                ))

            special_tax_types_4 = set(product_lines.tax_ids.filtered(
                lambda t: t.l10n_tw_edi_tax_type == '4'
            ).mapped('l10n_tw_edi_special_tax_type'))

            if "4" in invoice_lines_tax_types and len(special_tax_types_4) > 1:
                errors.append(self.env._(
                    "Special tax type cannot be mixed with other special tax types."
                ))

            special_tax_types_3 = set(product_lines.tax_ids.filtered(
                lambda t: t.l10n_tw_edi_tax_type == '3'
            ).mapped('l10n_tw_edi_special_tax_type'))

            if "3" in invoice_lines_tax_types and len(special_tax_types_3) > 1:
                errors.append(self.env._(
                    "Duty free with special tax type cannot be mixed with duty free without special tax type."
                ))

            if "3" in invoice_lines_tax_types and next(iter(special_tax_types_3)) == "8" and len(invoice_lines_tax_types) > 1:
                errors.append(self.env._(
                    "Duty free with special tax type cannot be mixed with other tax types."
                ))

            if {"2", "3"}.issubset(invoice_lines_tax_types):
                errors.append(self.env._(
                    "Tax type 2 (Zero tax rate) and type 3 (Duty free) cannot be used together."
                ))

            tax_type_1_rates = product_lines.tax_ids.filtered(
                lambda t: t.l10n_tw_edi_tax_type == '1'
            ).mapped('amount')

            if "1" in invoice_lines_tax_types and any(rate != 5 for rate in tax_type_1_rates):
                errors.append(self.env._(
                    "Amount for Taxable tax type must be 5%."
                ))
        else:
            errors.append(self.env._(
                "Please fill in the tax on the invoice lines and select the Ecpay tax type for taxes."
            ))
        return errors

    def _l10n_tw_edi_compute_tax_type_from_invoice_lines(self):
        """
        Calculate and return the tax type, special tax type and is zero tax rate included based on
        the taxes on invoice lines
        """
        self.ensure_one()
        product_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        # Create a set of tax types on invoice lines to check if there are multiple tax types or specific tax type on the invoice lines
        invoice_lines_tax_types = set(product_lines.tax_ids.mapped('l10n_tw_edi_tax_type'))

        tax_type = False
        special_tax_type = False
        is_zero_tax_rate = False

        if invoice_lines_tax_types:
            if len(invoice_lines_tax_types) > 1:  # mixed tax types
                tax_type = "9"
                special_tax_type = 0
                is_zero_tax_rate = "2" in invoice_lines_tax_types
            elif "4" in invoice_lines_tax_types:  # special tax rate
                tax_type = "4"
                special_tax_type = int(product_lines.tax_ids.mapped('l10n_tw_edi_special_tax_type')[0])
            elif "3" in invoice_lines_tax_types:
                tax_type = "3"
                special_tax_type = 8 if product_lines.tax_ids[0].l10n_tw_edi_special_tax_type == "8" else False
            else:
                tax_type = next(iter(invoice_lines_tax_types))
                special_tax_type = 0
                is_zero_tax_rate = "2" in invoice_lines_tax_types
        return tax_type, special_tax_type, is_zero_tax_rate

    def _l10n_tw_edi_convert_currency_to_twd(self, amount):
        """
        Convert currency to TWD if the currency is not TWD
        """
        self.ensure_one()
        if self.currency_id.name == "TWD":
            return amount
        return self.currency_id._convert(amount, self.env.ref("base.TWD"), self.company_id, self.invoice_date or self.date, round=False)

    def _reformat_phone_number(self, phone):
        cleaned_number = phone
        # Replace leading '+' with '0'
        if phone.startswith('+'):
            if ' ' in phone:
                parts = phone.split(' ', 1)
                cleaned_number = '0' + parts[1]
            else:
                cleaned_number = '0' + phone[1:]
        # Remove spaces, dashes, parentheses, etc.
        cleaned_number = re.sub(r'[^\d+]', '', cleaned_number)
        return cleaned_number

    def _l10n_tw_edi_check_before_generate_invoice_json(self):
        errors = []
        if not self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id:
            errors.append(self.env._("Please fill in the ECpay API information in the Setting!"))

        if (self.l10n_tw_edi_is_print or self.partner_id.vat) and not self.partner_id.contact_address:
            errors.append(self.env._("Please fill in the customer address for printing Ecpay invoice."))

        if not self.partner_id.email and not self.partner_id.phone:
            errors.append(self.env._("Please fill in the customer email or phone number for Ecpay invoice creation."))

        if self.partner_id.phone:
            if not self.partner_id.phone.startswith('+') or not re.match(r"\+\d{1,3} ", self.partner_id.phone):
                errors.append(self.env._("Phone number must start with country code and please add a space after the country code (i.e +866 234 567 890)."))
            formatted_phone = self._reformat_phone_number(self.partner_id.phone)
            if not re.fullmatch(r'[\d+ ]+', formatted_phone):
                errors.append(self.env._("Phone number contains invalid characters! Only digits, '+' and spaces are allowed."))

        if self.l10n_tw_edi_is_b2b and not self.partner_id.vat:
            errors.append(self.env._("Tax id is required for company contact or individual contact under a company."))

        if self.l10n_tw_edi_is_b2b and self.partner_id.vat and (not self.partner_id.vat.isdigit() or len(self.partner_id.vat) != 8):
            errors.append(self.env._("Tax id is invalid. Should be 8 digits."))

        errors.extend(self._l10n_tw_edi_check_tax_type_on_invoice_lines())

        tax_type, _, is_zero_tax_rate = self._l10n_tw_edi_compute_tax_type_from_invoice_lines()

        if self.l10n_tw_edi_invoice_type == "07" and tax_type not in ["1", "2", "3", "9"]:
            errors.append(self.env._(
                "Invoice type 07 must be used with tax type 1, 2, 3 or 9. Please check the tax type on the invoice lines."
            ))

        if self.l10n_tw_edi_invoice_type == "08" and tax_type not in ["3", "4"]:
            errors.append(self.env._(
                "Invoice type 08 must be used with tax type 3 or 4. Please check the tax type on the invoice lines."
            ))

        if is_zero_tax_rate:
            if not self.l10n_tw_edi_clearance_mark or not self.l10n_tw_edi_zero_tax_rate_reason:
                errors.append(self.env._(
                    "Clearance mark and Zero tax rate reason is required for zero tax rate invoice."
                ))
        if errors:
            if self.website_id:
                self.message_post(body="Error:\n" + "\n".join(errors))
            else:
                raise UserError("Error:\n" + "\n".join(errors))

    def _l10n_tw_edi_prepare_item_list(self, json_data, is_allowance=False):
        item_list = []
        sale_amount = 0
        tax_amount = 0
        AccountTax = self.env['account.tax']
        for line in self.invoice_line_ids.filtered(lambda line: line.display_type == "product"):

            base_line = self._prepare_product_base_line_for_taxes_computation(line)
            AccountTax._add_tax_details_in_base_line(base_line, self.company_id)

            twd_excluded_amount = base_line['tax_details']['raw_total_excluded']
            twd_included_amount = base_line['tax_details']['raw_total_included']

            tax_type, _, _ = self._l10n_tw_edi_compute_tax_type_from_invoice_lines()

            if self.l10n_tw_edi_is_b2b:
                item_price = self._l10n_tw_edi_rounding(twd_excluded_amount / line.quantity)
                item_amount = self._l10n_tw_edi_rounding(twd_excluded_amount)
            else:
                if not is_allowance and line.tax_ids and not line.tax_ids[0].price_include:
                    item_price = self._l10n_tw_edi_rounding(twd_excluded_amount / line.quantity)
                    item_amount = self._l10n_tw_edi_rounding(twd_excluded_amount)
                else:
                    item_price = self._l10n_tw_edi_rounding(twd_included_amount / line.quantity)
                    item_amount = self._l10n_tw_edi_rounding(twd_included_amount)

                item_amount_taxed = self._l10n_tw_edi_rounding(twd_included_amount)

            if self.l10n_tw_edi_is_b2b and is_allowance:
                item_list.append({
                    "OriginalInvoiceNumber": self.l10n_tw_edi_ecpay_invoice_id,
                    "OriginalInvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d"),
                    "OriginalSequenceNumber": line.sequence + 1,  # Cannot start from 0
                    "ItemName": line.product_id.name[:100],
                    "ItemCount": line.quantity,
                    "ItemPrice": item_price,
                    "ItemAmount": item_amount,
                })
            else:
                item_list.append({
                    "ItemSeq": line.sequence + 1,  # Cannot start from 0
                    "ItemName": line.product_id.name[:100],
                    "ItemCount": line.quantity,
                    "ItemWord": line.product_uom_id.name[:6],
                    "ItemPrice": item_price,
                    "ItemTaxType": line.tax_ids[0].l10n_tw_edi_tax_type if tax_type != "4" and line.tax_ids else "",
                    "ItemAmount": item_amount,
                })
            if self.l10n_tw_edi_is_b2b:
                sale_amount += item_amount
                tax_amount += base_line['tax_details']['taxes_data'][0]['raw_tax_amount']
            else:
                sale_amount += item_amount_taxed

        # Adjust the sale amount
        amount_on_invoice = self.amount_untaxed_signed if self.l10n_tw_edi_is_b2b else self.amount_total_signed
        difference = self.company_id.currency_id.round(sale_amount) - abs(amount_on_invoice)
        if difference != 0:
            item_list[-1]["ItemAmount"] -= difference
            item_list[-1]["ItemPrice"] = self._l10n_tw_edi_rounding(item_list[-1]["ItemAmount"] / item_list[-1]["ItemCount"])
            sale_amount -= difference

        # Credite note adjustment
        if is_allowance:
            # Check if the credit note has exchange difference, we need to add it to the sale amount
            reconciled_partials = self._get_all_reconciled_invoice_partials()
            exchange_difference = sum(item['amount'] for item in reconciled_partials if item.get('is_exchange'))
            item_list[-1]["ItemAmount"] += exchange_difference
            item_list[-1]["ItemPrice"] = self._l10n_tw_edi_rounding(item_list[-1]["ItemAmount"] / item_list[-1]["ItemCount"])
            sale_amount += exchange_difference

            # Check if the credit note has amount due, we need to add it to the sale amount
            item_list[-1]["ItemAmount"] += self.amount_residual_signed
            item_list[-1]["ItemPrice"] = self._l10n_tw_edi_rounding(item_list[-1]["ItemAmount"] / item_list[-1]["ItemCount"])
            sale_amount += self.amount_residual_signed

        if self.l10n_tw_edi_is_b2b and is_allowance:
            json_data["Details"] = item_list
        else:
            json_data["Items"] = item_list

        if not is_allowance:
            json_data["SalesAmount"] = self.company_id.currency_id.round(sale_amount)
        else:
            if self.l10n_tw_edi_is_b2b:
                json_data["TotalAmount"] = self.company_id.currency_id.round(sale_amount)
            else:
                json_data["AllowanceAmount"] = self.company_id.currency_id.round(sale_amount)

        if self.l10n_tw_edi_is_b2b:
            json_data["TaxAmount"] = self.company_id.currency_id.round(tax_amount) if tax_type != "4" else 0

    def _l10n_tw_edi_generate_invoice_json(self):
        self._l10n_tw_edi_check_before_generate_invoice_json()
        tax_type, special_tax_type, is_zero_tax_rate = self._l10n_tw_edi_compute_tax_type_from_invoice_lines()
        unique_key = f"{self.name}_{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.l10n_tw_edi_related_number = base64.urlsafe_b64encode(unique_key.encode("utf-8")).decode()
        formatted_phone = self._reformat_phone_number(self.partner_id.phone) if self.partner_id.phone else ""
        prduct_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        vat = "1" if prduct_lines[0].tax_ids and prduct_lines[0].tax_ids[0].price_include else "0"

        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": self.l10n_tw_edi_related_number,
            "CustomerIdentifier": self.partner_id.vat if self.l10n_tw_edi_is_b2b and self.partner_id.vat else "",
            "CustomerAddr": self.partner_id.contact_address,
            "CustomerEmail": self.partner_id.email or "",
            "CustomerPhone": formatted_phone,
            "InvType": self.l10n_tw_edi_invoice_type,
            "TaxType": tax_type,
            "InvoiceRemark": self.ref,
        }

        if special_tax_type:
            json_data["SpecialTaxType"] = special_tax_type

        self._l10n_tw_edi_prepare_item_list(json_data)

        if self.l10n_tw_edi_is_b2b:
            json_data["TotalAmount"] = json_data["SalesAmount"] + json_data["TaxAmount"]
        else:
            json_data.update({
                "CustomerName": self.partner_id.name,
                "Print": "1" if self.l10n_tw_edi_is_print or self.l10n_tw_edi_is_b2b else "0",
                "Donation": "1" if self.l10n_tw_edi_love_code else "0",
                "LoveCode": self.l10n_tw_edi_love_code or "",
                "CarrierType": self.l10n_tw_edi_carrier_type or "",
                "CarrierNum": self.l10n_tw_edi_carrier_number if self.l10n_tw_edi_carrier_type in ["2", "3", "4", "5"] else "",
                "CarrierNum2": self.l10n_tw_edi_carrier_number_2 if self.l10n_tw_edi_carrier_type in ["4", "5"] else "",
                "vat": vat,
            })

        if is_zero_tax_rate:
            json_data["ClearanceMark"] = self.l10n_tw_edi_clearance_mark
            json_data["ZeroTaxRateReason"] = self.l10n_tw_edi_zero_tax_rate_reason

        return json_data

    def _l10n_tw_edi_check_before_generate_issue_allowance_json(self):
        if not self.l10n_tw_edi_ecpay_invoice_id:
            raise UserError(self.env._(
                "You cannot issue an allowance for an invoice that was not sent to Ecpay. "
                "Invoice number: %(invoice_number)s", invoice_number=self.name))
        if not self.l10n_tw_edi_ecpay_invoice_id:
            raise UserError(self.env._(
                "You cannot issue an allowance for an invoice that was not sent to Ecpay. "
                "Invoice number: %(invoice_number)s", invoice_number=self.name))

        if (self.l10n_tw_edi_is_b2b or self.l10n_tw_edi_refund_agreement_type == "online") and not self.partner_id.email:
            raise UserError(self.env._("Customer email is needed for notification"))

        if not self.l10n_tw_edi_is_b2b and \
                ((self.l10n_tw_edi_allowance_notify_way == "email" and not self.partner_id.email) or (self.l10n_tw_edi_allowance_notify_way == "phone" and not self.partner_id.phone)):
            raise UserError(self.env._("Customer %(notify_way)s is needed for notification",
                                       notify_way=self.l10n_tw_edi_allowance_notify_way))

    def _l10n_tw_edi_generate_issue_allowance_json(self):
        self._l10n_tw_edi_check_before_generate_issue_allowance_json()
        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
        }

        self._l10n_tw_edi_prepare_item_list(json_data, is_allowance=True)

        if not self.l10n_tw_edi_is_b2b:
            if self.l10n_tw_edi_refund_agreement_type == "online":
                json_data["ReturnURL"] = urljoin(
                    self.get_base_url(),
                    f"/invoice/ecpay/agreed_invoice_allowance/{self.id}?access_token={self._portal_ensure_token()}")
            if self.l10n_tw_edi_allowance_notify_way == "email" and self.partner_id.email:
                json_data["AllowanceNotify"] = "E"
                json_data["NotifyMail"] = self.partner_id.email
            elif self.l10n_tw_edi_allowance_notify_way == "phone" and self.partner_id.phone:
                json_data["AllowanceNotify"] = "S"
                json_data["NotifyPhone"] = self.partner_id.phone.replace("+", "").replace(" ", "")

            json_data.update({
                "InvoiceNo": self.l10n_tw_edi_ecpay_invoice_id,
                "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            json_data.update({
                "AllowanceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
                "CustomerEmail": self.partner_id.email,
            })

        return json_data

    def _l10n_tw_edi_send(self, json_content):
        """
        Issuing an e-invoice by calling the Ecpay API and update the invoicing result in Odoo
        """
        self.ensure_one()
        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)

        ecpay_api = EcPayAPI(self.company_id, self.l10n_tw_edi_is_b2b)
        response_data = ecpay_api.call_ecpay_api("/Issue", json_content)
        if int(response_data.get("RtnCode")) != 1:
            return response_data.get("RtnMsg").split("\r\n")
        invoice_number = response_data.get("InvoiceNumber") if self.l10n_tw_edi_is_b2b else response_data.get("InvoiceNo")
        self.write({
            "l10n_tw_edi_ecpay_invoice_id": invoice_number,
            # The date return from Ecpay API used "+" instead of " "
            "l10n_tw_edi_invoice_create_date": fields.Datetime.now() if self.l10n_tw_edi_is_b2b else ecpay_api._transfer_time(
                response_data.get("InvoiceDate").replace("+", " ")),
            "l10n_tw_edi_state": "invoiced",
        })
        self._message_log(body=self.env._(
            "The invoice has been successfully sent to Ecpay with Ecpay invoice number %(invoice_number)s.",
            invoice_number=invoice_number
        ))

    def _l10n_tw_edi_update_ecpay_invoice_info(self):
        """
        Searching the e-invoice information from Ecpay API and update the invoice information in Odoo
        """
        self.ensure_one()
        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)

        if not self.l10n_tw_edi_related_number:
            raise UserError(self.env._("The invoice: %(invoice_name)s has no related number", invoice_id=self.name))

        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": self.l10n_tw_edi_related_number,
        }

        if self.l10n_tw_edi_is_b2b:
            json_data.update({
                "InvoiceCategory": 0,
                "InvoiceNumber": self.l10n_tw_edi_ecpay_invoice_id,
                "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            })

        response_data = EcPayAPI(self.company_id, self.l10n_tw_edi_is_b2b).call_ecpay_api("/GetIssue", json_data)
        if int(response_data.get("RtnCode")) != 1:
            return response_data.get("RtnMsg").split("\r\n")

        invalid_status = int(response_data.get("RtnData").get("Invalid_Status")) if self.l10n_tw_edi_is_b2b else int(response_data.get("IIS_Invalid_Status"))
        self.l10n_tw_edi_state = "valid" if invalid_status == 0 else "invalid"

    def _l10n_tw_edi_run_invoice_invalid(self):
        """
        Cancelling the e-invoice by calling the Ecpay API and update the invoice information in Odoo
        """
        self.ensure_one()

        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)

        if not self.l10n_tw_edi_ecpay_invoice_id:
            raise UserError(self.env._("You cannot invalidate an invoice that was not sent to Ecpay."))
        if self.l10n_tw_edi_state == "invalid":
            raise UserError(self.env._("The invoice: %(invoice_id)s has already been invalidated",
                                       invoice_id=self.l10n_tw_edi_ecpay_invoice_id))

        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "InvoiceDate": self.l10n_tw_edi_invoice_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Reason": self.l10n_tw_edi_invalidate_reason
        }

        if self.l10n_tw_edi_is_b2b:
            json_data["InvoiceNumber"] = self.l10n_tw_edi_ecpay_invoice_id
        else:
            json_data["InvoiceNo"] = self.l10n_tw_edi_ecpay_invoice_id

        response_data = EcPayAPI(self.company_id, self.l10n_tw_edi_is_b2b).call_ecpay_api("/Invalid", json_data)

        if int(response_data.get("RtnCode")) != 1:
            raise UserError(self.env._("Fail to invalidate invoice. Error message: %(error_message)s",
                                       error_message=response_data.get("RtnMsg")))

        # update the invoice information in Odoo
        self._l10n_tw_edi_update_ecpay_invoice_info()

        self._message_log(
            body=self.env._("Ecpay invoice number %(invoice_number)s has been invalidated successfully.",
                            invoice_number=self.l10n_tw_edi_ecpay_invoice_id),
        )

    def _l10n_tw_edi_issue_allowance(self, json_content):
        """
        Issuing an allowance by calling the Ecpay API and update the refund invoice information in Odoo
        Two methods to issue the allowance
        1. Endpoint: /Allowance
            General allowance, which requires merchants or sellers to get the agreement from the customer first
            (not by using ECPay system)
            and then to send an API request to ECPay to issue an allowance.
        2. Endpoint: /AllowanceByCollegiate
            Sending an API request to ECPay and ECPay will send an e-mail notification with a link to the customer to
            get his/her agreement
            ONce the customer clicks the link, an allowance will be issued instantly
        """
        self.ensure_one()

        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env["res.company"]._with_locked_records(self)

        query_param = "/AllowanceByCollegiate" if not self.l10n_tw_edi_is_b2b and self.l10n_tw_edi_refund_agreement_type == "online" else "/Allowance"

        response_data = EcPayAPI(self.company_id, self.l10n_tw_edi_is_b2b).call_ecpay_api(query_param, json_content)

        if int(response_data.get("RtnCode")) != 1:
            raise UserError(self.env._("Fail to issue allowance for ECpay invoice. Error message: %(error_message)s",
                                       error_message=response_data.get("RtnMsg")))

        if self.l10n_tw_edi_is_b2b:
            self.l10n_tw_edi_refund_invoice_number = response_data.get("AllowanceNo")
        else:
            self.write({
                "l10n_tw_edi_refund_invoice_number": response_data.get("IA_Allow_No"),
                "l10n_tw_edi_refund_state": "to_be_agreed" if self.l10n_tw_edi_refund_agreement_type == "online" else "agreed",
            })

        self._message_log(
            body=self.env._("Ecpay invoice number %(invoice_number)s has been issued allowance successfully.",
                            invoice_number=self.l10n_tw_edi_ecpay_invoice_id),
        )

    def _l10n_tw_edi_print_invoice(self):
        if self.l10n_tw_edi_state not in ['invoiced', 'valid'] or not self.l10n_tw_edi_ecpay_invoice_id or not (self.l10n_tw_edi_is_print or self.l10n_tw_edi_is_b2b):
            raise UserError(self.env._(
                "Cannot print the invoice that was not sent to Ecpay or the print flag is not set "
                "or the Ecpay inovice is invalid."
            ))
        return {
            "name": self.env._("Print Ecpay Invoice"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "l10n_tw_edi.invoice.print",
            "target": "new",
            "context": {
                "default_invoice_id": self.id,
            },
        }
