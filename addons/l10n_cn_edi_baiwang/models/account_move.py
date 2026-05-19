# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cn_fapiao_number = fields.Char(string="Fapiao Number", copy=False)
    l10n_cn_fapiao_date = fields.Date(string="Fapiao Date", copy=False)
    l10n_cn_edi_document_ids = fields.One2many(
        'l10n_cn_edi.document',
        'move_id',
        string="Baiwang Documents",
    )

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
            "invoiceTypeCode": "02",  # e.g., 02 for normal digital invoice
            "priceTaxMark": "0",  # 0 for tax exclusive based on your CSV note
            "buyerTaxNo": self.partner_id.vat or "",
            "buyerName": self.partner_id.name,
            "invoiceDetailsList": self._l10n_cn_prepare_baiwang_lines(),
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

    def action_request_baiwang_red_form(self):
        """ Triggered by user on a Draft Credit Note to request a Red Form. """
        self.ensure_one()

        # 1. Create the EDI Document link
        edi_doc = self.env['l10n_cn_edi.document'].create({
            'move_id': self.id,
            'state': 'draft',
        })

        # 2. Setup Client
        client = BaiwangClient(
            app_key=self.company_id.l10n_cn_baiwang_app_key,
            app_secret=self.company_id.l10n_cn_baiwang_app_secret,
            salt=self.company_id.l10n_cn_baiwang_salt,
        )

        # 3. Payload (Mapping from your 'Field & Parameter - redform - add.csv')
        payload = {
            "taxNo": self.company_id.vat,
            # ... map the original invoice details here ...
        }

        response = client.call_api("baiwang.output.redinvoice.add", payload, self.company_id.l10n_cn_baiwang_cached_token)

        if response.get("success"):
            # Save the UUID and set to pending!
            edi_doc.write({
                'baiwang_uuid': response.get("response", {}).get("redConfirmUuid"),
                'state': 'red_form_pending',
            })
            self.message_post(body="Red Form Requested. Waiting for counterpart confirmation.")
        else:
            edi_doc.write({'state': 'failed', 'error_message': response.get("errorResponse", {}).get("message")})

    def unlink(self):
        """ Prevent deletion of Credit Notes that have pending Red Forms. """
        for move in self:
            # Look for any EDI documents attached to this move that are pending
            pending_docs = self.env['l10n_cn_edi.document'].search([
                ('move_id', '=', move.id),
                ('state', '=', 'red_form_pending'),
            ], limit=1)

            if pending_docs:
                msg = (
                    "You cannot delete this Credit Note because a Red Form Request is "
                    "currently pending on the Golden Tax system.\n\n"
                    "If you need to cancel it, please revoke the Red Form on the Baiwang portal first."
                )
                raise UserError(
                    msg,
                )

        return super().unlink()
