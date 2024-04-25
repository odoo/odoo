# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _l10n_in_edi_generate_invoice_json(self, invoice):
        json_payload = super()._l10n_in_edi_generate_invoice_json(invoice)
        if json_payload['SellerDtls'].get('LglNm') and invoice.company_id.l10n_in_trade_name:
            json_payload['SellerDtls']['LglNm'] = invoice.company_id.l10n_in_trade_name
        return json_payload

    def _l10n_in_edi_ewaybill_generate_json(self, invoices):
        json_payload = super()._l10n_in_edi_ewaybill_generate_json(invoices)
        if not invoices.is_purchase_document(include_receipts=True) and json_payload.get('fromTrdName') and invoices.company_id.l10n_in_trade_name:
            json_payload['fromTrdName'] = invoices.company_id.l10n_in_trade_name
        return json_payload
