# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import _, api, models
from odoo.addons.l10n_tw_edi_ecpay.utils import EcPayAPI
from odoo.exceptions import UserError


class ReportEcpayInvoice(models.AbstractModel):
    _name = "report.l10n_tw_edi_ecpay.invoice"
    _description = "Ecpay Invoice Report"

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

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env["account.move"].browse(docids)
        ecpay_invoices_data = []

        for move in moves:
            if not move.l10n_tw_edi_related_number:
                raise UserError(_("Invoice %(move_name)s does not have Ecpay Invoice", move_name=move.name))

            json_data = {
                "MerchantID": self.env.user.company_id.l10n_tw_edi_ecpay_merchant_id,
                "RelateNumber": move.l10n_tw_edi_related_number,
            }

            ecpay_api = EcPayAPI(self.env.user.company_id)
            response_data = ecpay_api.call_ecpay_api("/GetIssue", json_data)
            if response_data.get('RtnCode') != 1:
                raise UserError(_("Invoice %(move_name)s Error: %(error)s", move_name=move.name, error=response_data.get('RtnMsg')))

            create_date_utc_time = ecpay_api._transfer_time(response_data.get("IIS_Create_Date").replace("+", " "))  # The date return from Ecpay API used "+" instead of " "

            ecpay_invoice_data = {
                "l10n_tw_edi_invoice_month": self._set_invoice_month(create_date_utc_time),
                "l10n_tw_edi_invoice_number": response_data.get("IIS_Number"),
                "l10n_tw_edi_invoice_create_date": create_date_utc_time,
                "l10n_tw_edi_invoice_random_number": response_data.get("IIS_Random_Number"),
                "l10n_tw_edi_invoice_tax_amount": response_data.get("IIS_Tax_Amount"),
                "l10n_tw_edi_invoice_amount": response_data.get("IIS_Sales_Amount"),
                "l10n_tw_edi_invoice_identifier": response_data.get("IIS_Identifier"),
                "l10n_tw_edi_invoice_carrier_type": response_data.get("IIS_Carrier_Type"),
                "l10n_tw_edi_invoice_carrier_number": response_data.get("IIS_Carrier_Num"),
                "l10n_tw_edi_invoice_category": response_data.get("IIS_Category"),
                "l10n_tw_edi_invoice_seller_identifier": self.env.company.l10n_tw_edi_ecpay_seller_identifier,
                "l10n_tw_edi_invoice_pos_barcode": response_data.get("PosBarCode"),
                "l10n_tw_edi_invoice_qr_code_left": response_data.get("QRCode_Left"),
                "l10n_tw_edi_invoice_qr_code_right": response_data.get("QRCode_Right"),
                "l10n_tw_edi_invoice_items": [],
            }
            for item in response_data.get('Items'):
                ecpay_invoice_data["l10n_tw_edi_invoice_items"].append({
                    "l10n_tw_edi_invoice_item_name": item.get("ItemName"),
                    "l10n_tw_edi_invoice_item_count": item.get("ItemCount"),
                    "l10n_tw_edi_invoice_item_price": item.get("ItemPrice"),
                    "l10n_tw_edi_invoice_item_amount": item.get("ItemAmount"),
                })

            ecpay_invoices_data.append(ecpay_invoice_data)

        return {
            'docs': moves,
            'data': ecpay_invoices_data,
        }
