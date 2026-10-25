# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_tw_edi_ecpay.utils import call_ecpay_api, transfer_time


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
    l10n_tw_edi_is_b2b = fields.Boolean(string="Is B2B", compute="_compute_l10n_tw_edi_is_b2b")

    @api.depends("partner_id")
    def _compute_l10n_tw_edi_is_b2b(self):
        for rec in self:
            rec.l10n_tw_edi_is_b2b = rec.partner_id.commercial_partner_id.is_company

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        companies = self.company_id
        if len(companies) > 1:
            raise UserError(self.env._("POS orders from different companies cannot be consolidated into one invoice."))

        source_order = self[0]
        if source_order.company_id.account_fiscal_country_id.code == 'TW':
            if len(self) > 1 and any(order.config_id.is_ecpay_enabled for order in self):
                raise UserError(self.env._("With EcPay enabled, POS orders cannot be consolidated into one invoice."))
            vals.update({
                'l10n_tw_edi_is_print': source_order.l10n_tw_edi_is_print,
                'l10n_tw_edi_love_code': source_order.l10n_tw_edi_love_code,
                'l10n_tw_edi_carrier_type': source_order.l10n_tw_edi_carrier_type,
                'l10n_tw_edi_carrier_number': source_order.l10n_tw_edi_carrier_number,
                'l10n_tw_edi_carrier_number_2': source_order.l10n_tw_edi_carrier_number_2,
            })
            if source_order.refunded_order_id:
                vals.update({
                    "l10n_tw_edi_ecpay_invoice_id": source_order.refunded_order_id.account_move.l10n_tw_edi_ecpay_invoice_id,
                    "l10n_tw_edi_invoice_create_date": source_order.refunded_order_id.account_move.l10n_tw_edi_invoice_create_date,
                    "l10n_tw_edi_refund_agreement_type": "offline",
                    "l10n_tw_edi_allowance_notify_way": "email",
                })
        return vals

    @api.model
    def _l10n_tw_edi_set_invoice_month(self, create_date):
        """Calculate the Taiwanese invoice billing period string.

        In Taiwan, electronic uniform invoices are issued based on the
        Minguo calendar and grouped into bimonthly periods.

        1. Year: The Minguo year is calculated by subtracting 1911 from the
           Western year (e.g., 2026 - 1911 = 115年(year)).
        2. Bimonthly Periods: Invoices are declared in fixed 2-month clusters:
           - Jan/Feb, Mar/Apr, May/Jun, Jul/Aug, Sep/Oct, Nov/Dec.
           - Even months round backward (e.g., February belongs to 1-2月(month)).
           - Odd months round forward (e.g., May belongs to 5-6月(month)).

        :param str create_date: UTC timestamp string ("YYYY-MM-DD HH:MM:SS")
        :return str: Formatted period (e.g., "115年5-6月")
        """
        invoice_create_date = datetime.datetime.strptime(create_date, "%Y-%m-%d %H:%M:%S")
        # Define the month range for every two months
        if invoice_create_date.month % 2 == 0:
            invoice_month = f"{invoice_create_date.year - 1911}年{invoice_create_date.month - 1}-{invoice_create_date.month}月"
        else:
            invoice_month = f"{invoice_create_date.year - 1911}年{invoice_create_date.month}-{invoice_create_date.month + 1}月"

        return invoice_month

    def l10n_tw_edi_get_uniform_invoice(self):
        self.ensure_one()
        invoice = self.account_move

        if not invoice:
            return {"ecpay_error": self.env._("No invoice found linked to this record.")}

        json_data = {
            "MerchantID": self.company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "RelateNumber": invoice.l10n_tw_edi_related_number,
        }

        response_data = call_ecpay_api("/GetIssue", json_data, self.company_id, invoice.l10n_tw_edi_is_b2b)
        json_response = {}
        if response_data.get('RtnCode') != 1:
            return {
                "ecpay_error": self.env._(
                    "\n Invoice number: %(invoice_name)s \n Error: %(rtn_msg)s",
                    invoice_name=invoice.name,
                    rtn_msg=response_data.get('RtnMsg'),
                ),
            }

        create_date = response_data.get("IIS_Create_Date")
        # The date return from Ecpay API used "+" instead of " "
        parsed_create_date = create_date and create_date.replace("+", " ")

        json_response.update({
            "invoice_month": self._l10n_tw_edi_set_invoice_month(parsed_create_date) if parsed_create_date else False,
            "iis_number": response_data.get("IIS_Number"),
            "iis_create_date": transfer_time(parsed_create_date) if parsed_create_date else False,
            "iis_random_number": response_data.get("IIS_Random_Number"),
            "iis_tax_amount": response_data.get("IIS_Tax_Amount"),
            "l10n_tw_edi_invoice_amount": response_data.get("IIS_Sales_Amount"),
            "iis_identifier": response_data.get("IIS_Identifier"),
            "iis_carrier_type": response_data.get("IIS_Carrier_Type"),
            "iis_carrier_num": response_data.get("IIS_Carrier_Num"),
            "iis_category": response_data.get("IIS_Category"),
            "l10n_tw_edi_ecpay_seller_identifier": self.company_id.vat,
            "pos_barcode": response_data.get("PosBarCode"),
            "qrcode_left": response_data.get("QRCode_Left"),
            "qrcode_right": response_data.get("QRCode_Right"),
            "company_logo_exist": bool(self.company_id.logo),
        })
        return json_response
