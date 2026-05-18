# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError
from .baiwang_client import BaiwangClient
import time

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cn_fapiao_number = fields.Char(string="Fapiao Number", copy=False)
    l10n_cn_fapiao_date = fields.Date(string="Fapiao Date", copy=False)

    def _l10n_cn_issue_fapiao(self):
        self.ensure_one()
        company = self.company_id

        client = BaiwangClient(
            app_key=company.l10n_cn_baiwang_app_key,
            app_secret=company.l10n_cn_baiwang_app_secret,
            salt=company.l10n_cn_baiwang_salt,
        )

        # Generate unique Serial Number (Move Name + Timestamp to avoid duplicates on retries)
        serial_no = f"{self.name}_{int(time.time())}"

        # Build Payload mapping (Based on your CSVs)
        payload = {
            "taxNo": company.vat,
            "serialNo": serial_no,
            "invoiceTypeCode": "02", # e.g., 02 for normal digital invoice
            "priceTaxMark": "0", # 0 for tax exclusive based on your CSV note
            "buyerTaxNo": self.partner_id.vat or "",
            "buyerName": self.partner_id.name,
            "invoiceDetailsList": self._l10n_cn_prepare_baiwang_lines()
        }

        # Make the call
        response = client.call_api("baiwang.output.invoice.issue", payload, company.l10n_cn_baiwang_cached_token)

        if response.get("success"):
            # Update Odoo with returned Fapiao Number
            self.l10n_cn_fapiao_number = response.get("response", {}).get("invoiceNumber")
            self.message_post(body=f"Fapiao Successfully Issued. No: {self.l10n_cn_fapiao_number}")
        else:
            # Handle Failure
            error_msg = response.get("errorResponse", {}).get("message", "Unknown Error")
            raise UserError(f"Baiwang Issuance Failed: {error_msg}")

    def _l10n_cn_prepare_baiwang_lines(self):
        """ Maps Odoo invoice lines to Baiwang goodsDetail list """
        lines = []
        for index, line in enumerate(self.invoice_line_ids.filtered(lambda l: not l.display_type), start=1):
            lines.append({
                "goodsLineNo": index,
                "goodsName": line.name,
                "goodsCode": line.product_id.l10n_cn_tax_category_code or "DEFAULT_CODE",
                "goodsQuantity": str(line.quantity),
                "goodsPrice": str(line.price_unit),
                "goodsTotalPrice": str(line.price_subtotal),
                # If you have taxes, map the percentage here
                "goodsTaxRate": str(line.tax_ids[0].amount / 100) if line.tax_ids else "0", 
            })
        return lines
