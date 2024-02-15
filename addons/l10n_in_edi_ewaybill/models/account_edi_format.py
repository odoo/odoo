# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
from datetime import timedelta
from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.tools import html_escape
from odoo.exceptions import AccessError
from odoo.addons.iap import jsonrpc
from odoo.addons.l10n_in_edi.models.account_edi_format import DEFAULT_IAP_ENDPOINT, DEFAULT_IAP_TEST_ENDPOINT

from .error_codes import ERROR_CODES

import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _l10n_in_edi_ewaybill_base_irn_or_direct(self, move):
        """
            There is two type of api call to create E-waybill
            1. base on IRN, IRN is number created when we do E-invoice
            2. direct call, when E-invoice not aplicable or it"s credit not
        """
        if move.move_type == "out_refund":
            return "direct"
        einvoice_in_edi_format = move.journal_id.edi_format_ids.filtered(lambda f: f.code == "in_einvoice_1_03")
        return einvoice_in_edi_format and einvoice_in_edi_format._get_move_applicability(move) and "irn" or "direct"

    def _is_compatible_with_journal(self, journal):
        if self.code == "in_ewaybill_1_03":
            # In the Invoice we have a button to send Ewaybill so not required to send it automatically.
            return False
        return super()._is_compatible_with_journal(journal)

    def _is_enabled_by_default_on_journal(self, journal):
        """
            It's sent with a button action on the invoice so it's disabled by default
        """
        self.ensure_one()
        if self.code == "in_ewaybill_1_03":
            return False
        return super()._is_enabled_by_default_on_journal(journal)

    def _get_move_applicability(self, invoice):
        self.ensure_one()
        if self.code != 'in_ewaybill_1_03':
            return super()._get_move_applicability(invoice)

        if invoice.is_invoice() and invoice.country_code == 'IN':
            res = {
                'post': self._l10n_in_edi_ewaybill_post_invoice_edi,
                'cancel': self._l10n_in_edi_ewaybill_cancel_invoice,
                'edi_content': self._l10n_in_edi_ewaybill_json_invoice_content,
            }
            base = self._l10n_in_edi_ewaybill_base_irn_or_direct(invoice)
            if base == 'irn':
                res.update({
                    'post': self._l10n_in_edi_ewaybill_irn_post_invoice_edi,
                    'edi_content': self._l10n_in_edi_ewaybill_irn_json_invoice_content,
                    })
            return res

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == "in_ewaybill_1_03" or super()._needs_web_services()

    def _l10n_in_edi_ewaybill_irn_json_invoice_content(self, move):
        return json.dumps(self._l10n_in_edi_irn_ewaybill_generate_json(move)).encode()

    def _l10n_in_edi_ewaybill_json_invoice_content(self, move):
        return json.dumps(self._l10n_in_edi_ewaybill_generate_json(move)).encode()

    def _check_move_configuration(self, move):
        if self.code != "in_ewaybill_1_03":
            return super()._check_move_configuration(move)
        error_message = []
        base = self._l10n_in_edi_ewaybill_base_irn_or_direct(move)
        if not move.l10n_in_type_id and base == "direct":
            error_message.append(_("- Document Type"))
        if not move.l10n_in_mode:
            error_message.append(_("- Transportation Mode"))
        elif move.l10n_in_mode == "0" and not move.l10n_in_transporter_id:
            error_message.append(_("- Transporter is required when E-waybill is managed by transporter"))
        elif move.l10n_in_mode == "0" and move.l10n_in_transporter_id and not move.l10n_in_transporter_id.vat:
            error_message.append(_("- Selected Transporter is missing GSTIN"))
        elif move.l10n_in_mode == "1":
            if not move.l10n_in_vehicle_no and move.l10n_in_vehicle_type:
                error_message.append(_("- Vehicle Number and Type is required when Transportation Mode is By Road"))
        elif move.l10n_in_mode in ("2", "3", "4"):
            if not move.l10n_in_transportation_doc_no and move.l10n_in_transportation_doc_date:
                error_message.append(_("- Transport document number and date is required when Transportation Mode is Rail,Air or Ship"))
        if error_message:
            error_message.insert(0, _("The following information are missing on the invoice (see eWayBill tab):"))
        goods_lines = move.invoice_line_ids.filtered(lambda line: not (line.display_type in ('line_section', 'line_note', 'rounding') or line.product_id.type == "service"))
        if not goods_lines:
            error_message.append(_('You need at least one product having "Product Type" as stockable or consumable.'))
        if base == "irn":
            # already checked by E-invoice (l10n_in_edi) so no need to check
            return error_message
        is_purchase = move.is_purchase_document(include_receipts=True)
        error_message += self._l10n_in_validate_partner(move.partner_id)
        error_message += self._l10n_in_validate_partner(move.company_id.partner_id, is_company=True)
        if not re.match("^.{1,16}$", is_purchase and move.ref or move.name):
            error_message.append(_("%s number should be set and not more than 16 characters",
                (is_purchase and "Bill Reference" or "Invoice")))
        for line in goods_lines:
            if line.product_id:
                hsn_code = self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
                if not hsn_code:
                    error_message.append(_("HSN code is not set in product %s", line.product_id.name))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_(
                        "Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name
                    ))
            else:
                error_message.append(_("product is required to get HSN code"))
        if error_message:
            error_message.insert(0, _("Impossible to send the Ewaybill."))
        return error_message

    def _l10n_in_edi_ewaybill_cancel_invoice(self, invoices):
        if self.code != "in_ewaybill_1_03":
            return super()._cancel_invoice_edi(invoices)
        response = {}
        res = {}
        ewaybill_response_json = invoices._get_l10n_in_edi_ewaybill_response_json()
        cancel_json = {
            "ewbNo": ewaybill_response_json.get("ewayBillNo") or ewaybill_response_json.get("EwbNo"),
            "cancelRsnCode": int(invoices.l10n_in_edi_cancel_reason),
            "CnlRem": invoices.l10n_in_edi_cancel_remarks,
        }
        response = self._l10n_in_edi_ewaybill_cancel(invoices.company_id, cancel_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(invoices.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_cancel(invoices.company_id, cancel_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "312" in error_codes:
                # E-waybill is already canceled
                # this happens when timeout from the Government portal but IRN is generated
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                error = []
                response = {"data": ""}
                odoobot = self.env.ref("base.partner_root")
                invoices.message_post(author_id=odoobot.id, body=
                    Markup("%s<br/>%s:<br/>%s") %(
                        _("Somehow this E-waybill has been canceled in the government portal before. You can verify by checking the details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)"),
                        _("Error"),
                        error_message
                    )
                )
            if "no-credit" in error_codes:
                res[invoices] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(invoices.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[invoices] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill_cancel.json" % (invoices.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "account.move",
                "res_id": invoices.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[invoices] = inv_res
        return res

    def _l10n_in_edi_ewaybill_irn_post_invoice_edi(self, invoices):
        response = {}
        res = {}
        generate_json = self._l10n_in_edi_irn_ewaybill_generate_json(invoices)
        response = self._l10n_in_edi_irn_ewaybill_generate(invoices.company_id, generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "1005" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_authenticate(invoices.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_irn_ewaybill_generate(invoices.company_id, generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "4002" in error_codes or "4026" in error_codes:
                # Get E-waybill by details in case of IRN is already generated
                # this happens when timeout from the Government portal but E-waybill is generated
                response = self._l10n_in_edi_irn_ewaybill_get(invoices.company_id, generate_json.get("Irn"))
                if not response.get("error"):
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    invoices.message_post(author_id=odoobot.id, body=
                        _("Somehow this E-waybill has been generated in the government portal before. You can verify by checking the invoice details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)")
                    )

            if "no-credit" in error_codes:
                res[invoices] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(invoices.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                blocking_level = "error"
                if "404" in error_codes or "waiting" in error_codes:
                    blocking_level = "warning"
                res[invoices] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_irn_ewaybill.json" % (invoices.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "account.move",
                "res_id": invoices.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[invoices] = inv_res
        return res

    def _l10n_in_edi_irn_ewaybill_generate_json(self, invoice):
        json_payload = {
            "Irn": invoice._get_l10n_in_edi_response_json().get("Irn"),
            "Distance": invoice.l10n_in_distance,
        }
        if invoice.l10n_in_mode == "0":
            json_payload.update({
                "TransId": invoice.l10n_in_transporter_id.vat,
                "TransName": invoice.l10n_in_transporter_id.name,
            })
        elif invoice.l10n_in_mode == "1":
            json_payload.update({
                "TransMode": invoice.l10n_in_mode,
                "VehNo": invoice.l10n_in_vehicle_no,
                "VehType": invoice.l10n_in_vehicle_type,
            })
        elif invoice.l10n_in_mode in ("2", "3", "4"):
            doc_date = invoice.l10n_in_transportation_doc_date
            json_payload.update({
                "TransMode": invoice.l10n_in_mode,
                "TransDocDt": doc_date and doc_date.strftime("%d/%m/%Y") or False,
                "TransDocNo": invoice.l10n_in_transportation_doc_no,
            })
        return json_payload

    def _l10n_in_edi_ewaybill_post_invoice_edi(self, invoices):
        response = {}
        res = {}
        generate_json = self._l10n_in_edi_ewaybill_generate_json(invoices)
        response = self._l10n_in_edi_ewaybill_generate(invoices.company_id, generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(invoices.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_generate(invoices.company_id, generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "604" in error_codes:
                # Get E-waybill by details in case of E-waybill is already generated
                # this happens when timeout from the Government portal but E-waybill is generated
                response = self._l10n_in_edi_ewaybill_get_by_consigner(
                    invoices.company_id, generate_json.get("docType"), generate_json.get("docNo"))
                if not response.get("error"):
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    invoices.message_post(author_id=odoobot.id, body=
                        _("Somehow this E-waybill has been generated in the government portal before. You can verify by checking the invoice details into the government (https://ewaybillgst.gov.in/Others/EBPrintnew.asp)")
                    )
            if "no-credit" in error_codes:
                res[invoices] = {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(invoices.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                blocking_level = "error"
                if "404" in error_codes:
                    blocking_level = "warning"
                res[invoices] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": blocking_level,
                }
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_ewaybill.json" % (invoices.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "account.move",
                "res_id": invoices.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            res[invoices] = inv_res
        return res

    def _l10n_in_edi_ewaybill_get_error_message(self, code):
        error_message = ERROR_CODES.get(code)
        return error_message or _("We don't know the error message for this error code. Please contact support.")

    def _get_l10n_in_edi_saler_buyer_party(self, move):
        res = super()._get_l10n_in_edi_saler_buyer_party(move)
        if move.is_purchase_document(include_receipts=True):
            res = {
                "seller_details":  move.partner_id,
                "dispatch_details": move.partner_shipping_id or move.partner_id,
                "buyer_details": move.company_id.partner_id,
                "ship_to_details": move._l10n_in_get_warehouse_address() or move.company_id.partner_id,
            }
        return res

    def _l10n_in_edi_ewaybill_generate_json(self, invoices):
        def get_transaction_type(seller_details, dispatch_details, buyer_details, ship_to_details):
            """
                1 - Regular
                2 - Bill To - Ship To
                3 - Bill From - Dispatch From
                4 - Combination of 2 and 3
            """
            if seller_details != dispatch_details and buyer_details != ship_to_details:
                return 4
            elif seller_details != dispatch_details:
                return 3
            elif buyer_details != ship_to_details:
                return 2
            else:
                return 1

        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(invoices)
        seller_details = saler_buyer.get("seller_details")
        dispatch_details = saler_buyer.get("dispatch_details")
        buyer_details = saler_buyer.get("buyer_details")
        ship_to_details = saler_buyer.get("ship_to_details")
        sign = invoices.is_inbound() and -1 or 1
        extract_digits = self._l10n_in_edi_extract_digits
        tax_details = self._l10n_in_prepare_edi_tax_details(invoices)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        invoice_line_tax_details = tax_details.get("tax_details_per_record")
        json_payload = {
            "supplyType": invoices.is_purchase_document(include_receipts=True) and "I" or "O",
            "subSupplyType": invoices.l10n_in_type_id.sub_type_code,
            "docType": invoices.l10n_in_type_id.code,
            "transactionType": get_transaction_type(seller_details, dispatch_details, buyer_details, ship_to_details),
            "transDistance": str(invoices.l10n_in_distance),
            "docNo": invoices.is_purchase_document(include_receipts=True) and invoices.ref or invoices.name,
            "docDate": invoices.date.strftime("%d/%m/%Y"),
            "fromGstin": seller_details.commercial_partner_id.vat or "URP",
            "fromTrdName": seller_details.commercial_partner_id.name,
            "fromAddr1": dispatch_details.street or "",
            "fromAddr2": dispatch_details.street2 or "",
            "fromPlace": dispatch_details.city or "",
            "fromPincode": dispatch_details.country_id.code == "IN" and int(extract_digits(dispatch_details.zip)) or "",
            "fromStateCode": int(seller_details.state_id.l10n_in_tin) or "",
            "actFromStateCode": dispatch_details.state_id.l10n_in_tin and int(dispatch_details.state_id.l10n_in_tin) or "",
            "toGstin": buyer_details.commercial_partner_id.vat or "URP",
            "toTrdName": buyer_details.commercial_partner_id.name,
            "toAddr1": ship_to_details.street or "",
            "toAddr2": ship_to_details.street2 or "",
            "toPlace": ship_to_details.city or "",
            "toPincode": int(extract_digits(ship_to_details.zip)),
            "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
            "toStateCode": invoices.l10n_in_state_id.l10n_in_tin and int(invoices.l10n_in_state_id.l10n_in_tin) or (
                buyer_details.state_id.l10n_in_tin or int(buyer_details.state_id.l10n_in_tin) or ""
            ),
            "itemList": [
                self._get_l10n_in_edi_ewaybill_line_details(line, line_tax_details, sign)
                for line, line_tax_details in invoice_line_tax_details.items()
            ],
            "totalValue": self._l10n_in_round_value(tax_details.get("base_amount")),
            "cgstValue": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
            "sgstValue": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
            "igstValue": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
            "cessValue": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00)),
            "cessNonAdvolValue": self._l10n_in_round_value(tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "otherValue": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00)),
            "totInvValue": self._l10n_in_round_value((tax_details.get("base_amount") + tax_details.get("tax_amount"))),
        }
        is_overseas = invoices.l10n_in_gst_treatment in ("overseas", "special_economic_zone")
        if invoices.is_purchase_document(include_receipts=True):
            if is_overseas:
                json_payload.update({"fromStateCode": 99})
            if is_overseas and dispatch_details.state_id.country_id.code != "IN":
                json_payload.update({
                    "actFromStateCode": 99,
                    "fromPincode": 999999,
                })
            else:
                json_payload.update({
                    "actFromStateCode": dispatch_details.state_id.l10n_in_tin and int(dispatch_details.state_id.l10n_in_tin) or "",
                    "fromPincode": int(extract_digits(dispatch_details.zip)),
                })
        else:
            if is_overseas:
                json_payload.update({"toStateCode": 99})
            if is_overseas and ship_to_details.state_id.country_id.code != "IN":
                json_payload.update({
                    "actToStateCode": 99,
                    "toPincode": 999999,
                })
            else:
                json_payload.update({
                    "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
                    "toPincode": int(extract_digits(ship_to_details.zip)),
                })

        if invoices.l10n_in_mode == "0":
            json_payload.update({
                "transporterId": invoices.l10n_in_transporter_id.vat or "",
                "transporterName": invoices.l10n_in_transporter_id.name or "",
            })
        if invoices.l10n_in_mode in ("2", "3", "4"):
            json_payload.update({
                "transMode": invoices.l10n_in_mode,
                "transDocNo": invoices.l10n_in_transportation_doc_no or "",
                "transDocDate": invoices.l10n_in_transportation_doc_date and
                    invoices.l10n_in_transportation_doc_date.strftime("%d/%m/%Y") or "",
            })
        if invoices.l10n_in_mode == "1":
            json_payload.update({
                "transMode": invoices.l10n_in_mode,
                "vehicleNo": invoices.l10n_in_vehicle_no or "",
                "vehicleType": invoices.l10n_in_vehicle_type or "",
            })
        return json_payload

    def _get_l10n_in_edi_ewaybill_line_details(self, line, line_tax_details, sign):
        extract_digits = self._l10n_in_edi_extract_digits
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details.get("tax_details", {}))
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": extract_digits(line.product_id.l10n_in_hsn_code),
            "productDesc": line.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split("-")[0] or "OTH",
            "taxableAmount": self._l10n_in_round_value(line.balance * sign),
        }
        if tax_details_by_code.get("igst_rate") or (line.move_id.l10n_in_state_id.l10n_in_tin != line.company_id.state_id.l10n_in_tin):
            line_details.update({"igstRate": self._l10n_in_round_value(tax_details_by_code.get("igst_rate", 0.00))})
        else:
            line_details.update({
                "cgstRate": self._l10n_in_round_value(tax_details_by_code.get("cgst_rate", 0.00)),
                "sgstRate": self._l10n_in_round_value(tax_details_by_code.get("sgst_rate", 0.00)),
            })
        if tax_details_by_code.get("cess_rate"):
            line_details.update({"cessRate": self._l10n_in_round_value(tax_details_by_code.get("cess_rate"))})
        return line_details

    #================================ E-invoice API methods ===========================

    @api.model
    def _l10n_in_edi_irn_ewaybill_generate(self, company, json_payload):
        # IRN is created by E-invoice API call so waiting for it.
        if not json_payload.get("Irn"):
            return {"error": [{
                "code": "waiting",
                "message": _("waiting For IRN generation To create E-waybill")}
            ]}
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        params = {
            "auth_token": token,
            "json_payload": json_payload,
        }
        return self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/generate_ewaybill_by_irn", params=params)

    @api.model
    def _l10n_in_edi_irn_ewaybill_get(self, company, irn):
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        params = {
            "auth_token": token,
            "irn": irn,
        }
        return self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/get_ewaybill_by_irn", params=params)

    #=============================== E-waybill API methods ===================================

    @api.model
    def _l10n_in_edi_ewaybill_no_config_response(self):
        return {"error": [{
            "code": "0",
            "message": _(
                "Unable to send E-waybill."
                "Create an API user in NIC portal, and set it using the top menu: Configuration > Settings."
            )}
        ]}

    @api.model
    def _l10n_in_edi_ewaybill_check_authentication(self, company):
        sudo_company = company.sudo()
        if sudo_company.l10n_in_edi_ewaybill_username and sudo_company._l10n_in_edi_ewaybill_token_is_valid():
            return True
        elif sudo_company.l10n_in_edi_ewaybill_username and sudo_company.l10n_in_edi_ewaybill_password:
            authenticate_response = self._l10n_in_edi_ewaybill_authenticate(company)
            if not authenticate_response.get("error"):
                return True
        return False

    def _l10n_in_set_missing_error_message(self, response):
        for error in response.get('error', []):
            if error.get('code') and not error.get('message'):
                error['message'] = self._l10n_in_edi_ewaybill_get_error_message(error.get('code'))
        return response

    @api.model
    def _l10n_in_edi_ewaybill_connect_to_server(self, company, url_path, params):
        user_token = self.env["iap.account"].get("l10n_in_edi")
        params.update({
            "account_token": user_token.account_token,
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "username": company.sudo().l10n_in_edi_ewaybill_username,
            "gstin": company.vat,
        })
        if company.sudo().l10n_in_edi_production_env:
            default_endpoint = DEFAULT_IAP_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_in_edi_ewaybill.endpoint", default_endpoint)
        url = "%s%s" % (endpoint, url_path)
        try:
            response = jsonrpc(url, params=params, timeout=70)
            return self._l10n_in_set_missing_error_message(response)
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                "error": [{
                    "code": "access_error",
                    "message": _("Unable to connect to the E-WayBill service."
                        "The web service may be temporary down. Please try again in a moment.")
                }]
            }

    @api.model
    def _l10n_in_edi_ewaybill_authenticate(self, company):
        params = {"password": company.sudo().l10n_in_edi_ewaybill_password}
        response = self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/authenticate", params=params
        )
        if response and response.get("status_cd") == "1":
            company.sudo().l10n_in_edi_ewaybill_auth_validity = fields.Datetime.now() + timedelta(
                hours=6, minutes=00, seconds=00)
        return response

    @api.model
    def _l10n_in_edi_ewaybill_generate(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/generate", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_cancel(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/cancel", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_get_by_consigner(self, company, document_type, document_number):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"document_type": document_type, "document_number": document_number}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_ewaybill/1/getewaybillgeneratedbyconsigner", params=params
        )
