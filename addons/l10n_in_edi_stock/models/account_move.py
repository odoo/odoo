# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_in_edi_stock_prepare_invoice_json(self):
        def filter_to_apply(tax_values):
            if tax_values["base_line_id"].is_rounding_line:
                return False
            if tax_values["base_line_id"].product_id.type == 'service':
                return False
            return True

        self.ensure_one()
        saler_buyer = self.env['account.edi.format']._get_l10n_in_edi_saler_buyer_party(self)
        seller_details = saler_buyer.get('seller_details')
        dispatch_details = saler_buyer.get('dispatch_details')
        buyer_details = saler_buyer.get('buyer_details')
        ship_to_details = saler_buyer.get('ship_to_details')
        sign = self.is_inbound() and -1 or 1
        is_export = False
        is_import = False
        if self.l10n_in_gst_treatment == 'overseas':
            if self.is_purchase_document(include_receipts=True):
                is_import = True
            else:
                is_export = True
        rounding_function = self.env['account.edi.format']._l10n_in_round_value
        extract_digits = self.env['account.edi.format']._l10n_in_edi_extract_digits
        tax_details = self.env['account.edi.format']._l10n_in_prepare_edi_tax_details(self, filter_to_apply)
        tax_details_by_code = self.env['account.edi.format']._get_l10n_in_tax_details_by_line_code(
            tax_details.get("tax_details", {}))
        invoice_line_tax_details = tax_details.get("invoice_line_tax_details")
        json_payload = {
            "supplyType": ('in_' in self.move_type) and 'I' or 'O',
            "docNo": self.is_purchase_document(include_receipts=True) and self.ref or self.name,
            "docDate": self.date.strftime('%d/%m/%Y'),
            "fromGstin": not is_import and seller_details.commercial_partner_id.vat or 'URP',
            "fromTrdName": seller_details.commercial_partner_id.name,
            "fromStateCode": is_import and 99 or (int(self.l10n_in_state_id.l10n_in_tin)
                if ('in_' in self.move_type) and self.l10n_in_state_id else int(seller_details.state_id.l10n_in_tin)),
            "fromAddr1": dispatch_details.street or '',
            "fromAddr2": dispatch_details.street2 or '',
            "fromPlace": dispatch_details.city or '',
            "fromPincode": int(extract_digits(dispatch_details.zip)),
            "actFromStateCode": int(dispatch_details.state_id.l10n_in_tin),
            "toGstin": not is_export and buyer_details.commercial_partner_id.vat or 'URP',
            "toTrdName": buyer_details.commercial_partner_id.name,
            "toStateCode": is_export and 99 or (int(self.l10n_in_state_id.l10n_in_tin)
                if ('out_' in self.move_type) and self.l10n_in_state_id else int(buyer_details.state_id.l10n_in_tin)),
            "toAddr1": ship_to_details.street or '',
            "toAddr2": ship_to_details.street2 or '',
            "toPlace": ship_to_details.city or '',
            "toPincode": int(extract_digits(ship_to_details.zip)),
            "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
            "itemList": [
                self._get_l10n_in_edi_stock_line_details(line, line_tax_details, sign, rounding_function)
                for line, line_tax_details in invoice_line_tax_details.items()
            ],
            "totalValue": rounding_function(tax_details.get("base_amount") * sign),
            "cgstValue": rounding_function(tax_details_by_code.get("cgst_amount", 0.00) * sign),
            "sgstValue": rounding_function(tax_details_by_code.get("sgst_amount", 0.00) * sign),
            "igstValue": rounding_function(tax_details_by_code.get("igst_amount", 0.00) * sign),
            "cessValue": rounding_function(tax_details_by_code.get("cess_amount", 0.00) * sign),
            "cessNonAdvolValue": rounding_function(tax_details_by_code.get("cess_non_advol_amount", 0.00) * sign),
            "otherValue": rounding_function(tax_details_by_code.get("other_amount", 0.00) * sign),
            "totInvValue": rounding_function((tax_details.get("base_amount") + tax_details.get("tax_amount")) * sign),
        }

        return json_payload

    def _get_l10n_in_edi_stock_line_details(self, line, line_tax_details, sign, rounding_function):
        tax_details_by_code = self.env['account.edi.format']._get_l10n_in_tax_details_by_line_code(
            line_tax_details.get("tax_details", {}))
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": line.product_id.l10n_in_hsn_code,
            "productDesc": line.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split('-')[0] or 'OTH',
            "taxableAmount": rounding_function(line.balance * sign),
        }
        if tax_details_by_code.get("cgst_rate") and tax_details_by_code.get("sgst_rate"):
            line_details.update({
                "cgstRate": rounding_function(tax_details_by_code.get("cgst_rate")),
                "sgstRate": rounding_function(tax_details_by_code.get("sgst_rate")),
            })
        if tax_details_by_code.get("igst_rate"):
            line_details.update({"igstRate": rounding_function(tax_details_by_code.get("igst_rate"))})
        if tax_details_by_code.get("cess_rate"):
            line_details.update({"cessRate": rounding_function(tax_details_by_code.get("cess_rate"))})
        return line_details

    def _l10n_in_edi_stock_validate_move(self):
        if not self:
            return []
        self.ensure_one()
        error_message = []
        if not re.match("^.{1,16}$", self.is_purchase_document(include_receipts=True) and self.ref or self.name):
            error_message.append(_("Invoice number should not be more than 16 characters"))
        for line in self.invoice_line_ids.filtered(
            lambda line: not (line.display_type or line.is_rounding_line or line.product_id.type == 'service')):
            if line.product_id:
                hsn_code = self.env['account.edi.format']._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
                if not hsn_code:
                    error_message.append(_("- HSN code is not set in product %s", line.product_id.name))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_("- Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name))
            else:
                error_message.append(_("- product is required to get HSN code"))
        return error_message
