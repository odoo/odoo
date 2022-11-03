# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
import pytz
import markupsafe

from odoo import models, fields, api, _
from odoo.tools import html_escape, float_is_zero
from odoo.exceptions import AccessError
from odoo.addons.iap import jsonrpc
import logging

_logger = logging.getLogger(__name__)

DEFAULT_IAP_ENDPOINT = "https://l10n-in-edi.api.odoo.com"
DEFAULT_IAP_TEST_ENDPOINT = "https://l10n-in-edi-demo.api.odoo.com"


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _is_enabled_by_default_on_journal(self, journal):
        self.ensure_one()
        if self.code == "in_einvoice_1_03":
            return journal.company_id.country_id.code == 'IN'
        return super()._is_enabled_by_default_on_journal(journal)

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'in_einvoice_1_03':
            return super()._get_move_applicability(move)

        if move.is_sale_document() and move.country_code == 'IN' and move.l10n_in_gst_treatment in (
            "regular",
            "composition",
            "overseas",
            "special_economic_zone",
            "deemed_export",
        ):
            return {
                'post': self._l10n_in_edi_post_invoice,
                'cancel': self._l10n_in_edi_cancel_invoice,
                'edi_content': self._l10n_in_edi_xml_invoice_content,
            }

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == "in_einvoice_1_03" or super()._needs_web_services()

    def _l10n_in_edi_xml_invoice_content(self, invoice):
        return json.dumps(self._l10n_in_edi_generate_invoice_json(invoice)).encode()

    def _l10n_in_edi_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    def _check_move_configuration(self, move):
        if self.code != "in_einvoice_1_03":
            return super()._check_move_configuration(move)
        error_message = []
        error_message += self._l10n_in_validate_partner(move.partner_id)
        error_message += self._l10n_in_validate_partner(move.company_id.partner_id, is_company=True)
        if not re.match("^.{1,16}$", move.name):
            error_message.append(_("Invoice number should not be more than 16 characters"))
        for line in move.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section', 'rounding')):
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
        return error_message

    def _l10n_in_edi_get_iap_buy_credits_message(self, company):
        base_url = "https://iap-sandbox.odoo.com/iap/1/credit" if not company.sudo().l10n_in_edi_production_env else ""
        url = self.env["iap.account"].get_credits_url(service_name="l10n_in_edi", base_url=base_url)
        return markupsafe.Markup("""<p><b>%s</b></p><p>%s <a href="%s">%s</a></p>""") % (
            _("You have insufficient credits to send this document!"),
            _("Please buy more credits and retry: "),
            url,
            _("Buy Credits")
        )

    def _l10n_in_edi_post_invoice(self, invoice):
        generate_json = self._l10n_in_edi_generate_invoice_json(invoice)
        response = self._l10n_in_edi_generate(invoice.company_id, generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "1005" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_authenticate(invoice.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_generate(invoice.company_id, generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "2150" in error_codes:
                # Get IRN by details in case of IRN is already generated
                # this happens when timeout from the Government portal but IRN is generated
                response = self._l10n_in_edi_get_irn_by_details(invoice.company_id, {
                    "doc_type": invoice.move_type == "out_refund" and "CRN" or "INV",
                    "doc_num": invoice.name,
                    "doc_date": invoice.invoice_date and invoice.invoice_date.strftime("%d/%m/%Y") or False,
                })
                if not response.get("error"):
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    invoice.message_post(author_id=odoobot.id, body=_(
                        "Somehow this invoice had been submited to government before." \
                        "<br/>Normally, this should not happen too often" \
                        "<br/>Just verify value of invoice by uploade json to government website " \
                        "<a href='https://einvoice1.gst.gov.in/Others/VSignedInvoice'>here<a>."
                    ))
            if "no-credit" in error_codes:
                return {invoice: {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(invoice.company_id),
                    "blocking_level": "error",
                }}
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                return {invoice: {
                    "success": False,
                    "error": error_message,
                    "blocking_level": ("404" in error_codes) and "warning" or "error",
                }}
        if not response.get("error"):
            json_dump = json.dumps(response.get("data"))
            json_name = "%s_einvoice.json" % (invoice.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "account.move",
                "res_id": invoice.id,
                "mimetype": "application/json",
            })
            return {invoice: {"success": True, "attachment": attachment}}

    def _l10n_in_edi_cancel_invoice(self, invoice):
        l10n_in_edi_response_json = invoice._get_l10n_in_edi_response_json()
        cancel_json = {
            "Irn": l10n_in_edi_response_json.get("Irn"),
            "CnlRsn": invoice.l10n_in_edi_cancel_reason,
            "CnlRem": invoice.l10n_in_edi_cancel_remarks,
        }
        response = self._l10n_in_edi_cancel(invoice.company_id, cancel_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "1005" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_authenticate(invoice.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_cancel(invoice.company_id, cancel_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "9999" in error_codes:
                response = {}
                odoobot = self.env.ref("base.partner_root")
                invoice.message_post(author_id=odoobot.id, body=_(
                    "Somehow this invoice had been cancelled to government before." \
                    "<br/>Normally, this should not happen too often" \
                    "<br/>Just verify by logging into government website " \
                    "<a href='https://einvoice1.gst.gov.in'>here<a>."
                ))
            if "no-credit" in error_codes:
                return {invoice: {
                    "success": False,
                    "error": self._l10n_in_edi_get_iap_buy_credits_message(invoice.company_id),
                    "blocking_level": "error",
                }}
            else:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                return {invoice: {
                    "success": False,
                    "error": error_message,
                    "blocking_level": ("404" in error_codes) and "warning" or "error",
                }}
        if not response.get("error"):
            json_dump = json.dumps(response.get("data", {}))
            json_name = "%s_cancel_einvoice.json" % (invoice.name.replace("/", "_"))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "account.move",
                "res_id": invoice.id,
                "mimetype": "application/json",
            })
            return {invoice: {"success": True, "attachment": attachment}}

    def _l10n_in_validate_partner(self, partner, is_company=False):
        self.ensure_one()
        message = []
        if not re.match("^.{3,100}$", partner.street or ""):
            message.append(_("\n- Street required min 3 and max 100 characters"))
        if partner.street2 and not re.match("^.{3,100}$", partner.street2):
            message.append(_("\n- Street2 should be min 3 and max 100 characters"))
        if not re.match("^.{3,100}$", partner.city or ""):
            message.append(_("\n- City required min 3 and max 100 characters"))
        if not re.match("^.{3,50}$", partner.state_id.name or ""):
            message.append(_("\n- State required min 3 and max 50 characters"))
        if partner.country_id.code == "IN" and not re.match("^[0-9]{6,}$", partner.zip or ""):
            message.append(_("\n- Zip code required 6 digits"))
        if partner.phone and not re.match("^[0-9]{10,12}$",
            self._l10n_in_edi_extract_digits(partner.phone)
        ):
            message.append(_("\n- Mobile number should be minimum 10 or maximum 12 digits"))
        if partner.email and (
            not re.match(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$", partner.email)
            or not re.match("^.{6,100}$", partner.email)
        ):
            message.append(_("\n- Email address should be valid and not more then 100 characters"))
        return message

    def _get_l10n_in_edi_saler_buyer_party(self, move):
        return {
            "seller_details": move.company_id.partner_id,
            "dispatch_details": move._l10n_in_get_warehouse_address() or move.company_id.partner_id,
            "buyer_details": move.partner_id,
            "ship_to_details": move.partner_shipping_id or move.partner_id,
        }

    @api.model
    def _get_l10n_in_edi_partner_details(self, partner, set_vat=True, set_phone_and_email=True,
            is_overseas=False, pos_state_id=False):
        """
            Create the dictionary based partner details
            if set_vat is true then, vat(GSTIN) and legal name(LglNm) is added
            if set_phone_and_email is true then phone and email is add
            if set_pos is true then state code from partner or passed state_id is added as POS(place of supply)
            if is_overseas is true then pin is 999999 and GSTIN(vat) is URP and Stcd is .
            if pos_state_id is passed then we use set POS
        """
        partner_details = {
            "Addr1": partner.street or "",
            "Loc": partner.city or "",
            "Pin": int(self._l10n_in_edi_extract_digits(partner.zip)),
            "Stcd": partner.state_id.l10n_in_tin or "",
        }
        if partner.street2:
            partner_details.update({"Addr2": partner.street2})
        if set_phone_and_email:
            if partner.email:
                partner_details.update({"Em": partner.email})
            if partner.phone:
                partner_details.update({"Ph": self._l10n_in_edi_extract_digits(partner.phone)})
        if pos_state_id:
            partner_details.update({"POS": pos_state_id.l10n_in_tin or ""})
        if set_vat:
            partner_details.update({
                "LglNm": partner.commercial_partner_id.name,
                "GSTIN": partner.vat or "",
            })
        else:
            partner_details.update({"Nm": partner.name})
        if is_overseas:
            partner_details.update({
                "GSTIN": "URP",
                "Pin": 999999,
                "Stcd": "96",
                "POS": "96",
            })
        return partner_details

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        value = round(amount, precision_digits)
        # avoid -0.0
        return value if value else 0.0

    def _get_l10n_in_edi_line_details(self, index, line, line_tax_details):
        """
        Create the dictionary with line details
        return {
            account.move.line('1'): {....},
            account.move.line('2'): {....},
            ....
        }
        """
        sign = line.move_id.is_inbound() and -1 or 1
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details.get("tax_details", {}))
        full_discount_or_zero_quantity = line.discount == 100.00 or float_is_zero(line.quantity, 3)
        if full_discount_or_zero_quantity:
            unit_price_in_inr = line.currency_id._convert(
                line.price_unit,
                line.company_currency_id,
                line.company_id,
                line.date or fields.Date.context_today(self)
                )
        else:
            unit_price_in_inr = ((sign * line.balance) / (1 - (line.discount / 100))) / line.quantity
        return {
            "SlNo": str(index),
            "PrdDesc": line.name.replace("\n", ""),
            "IsServc": line.product_id.type == "service" and "Y" or "N",
            "HsnCd": self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code),
            "Qty": self._l10n_in_round_value(line.quantity or 0.0, 3),
            "Unit": line.product_uom_id.l10n_in_code and line.product_uom_id.l10n_in_code.split("-")[0] or "OTH",
            # Unit price in company currency and tax excluded so its different then price_unit
            "UnitPrice": self._l10n_in_round_value(unit_price_in_inr, 3),
            # total amount is before discount
            "TotAmt": self._l10n_in_round_value(unit_price_in_inr * line.quantity),
            "Discount": self._l10n_in_round_value((unit_price_in_inr * line.quantity) * (line.discount / 100)),
            "AssAmt": self._l10n_in_round_value((sign * line.balance)),
            "GstRt": self._l10n_in_round_value(tax_details_by_code.get("igst_rate", 0.00) or (
                tax_details_by_code.get("cgst_rate", 0.00) + tax_details_by_code.get("sgst_rate", 0.00)), 3),
            "IgstAmt": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
            "CgstAmt": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
            "SgstAmt": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
            "CesRt": self._l10n_in_round_value(tax_details_by_code.get("cess_rate", 0.00), 3),
            "CesAmt": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00)),
            "CesNonAdvlAmt": self._l10n_in_round_value(
                tax_details_by_code.get("cess_non_advol_amount", 0.00)),
            "StateCesRt": self._l10n_in_round_value(tax_details_by_code.get("state_cess_rate_amount", 0.00), 3),
            "StateCesAmt": self._l10n_in_round_value(tax_details_by_code.get("state_cess_amount", 0.00)),
            "StateCesNonAdvlAmt": self._l10n_in_round_value(
                tax_details_by_code.get("state_cess_non_advol_amount", 0.00)),
            "OthChrg": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00)),
            "TotItemVal": self._l10n_in_round_value(((sign * line.balance) + line_tax_details.get("tax_amount", 0.00))),
        }

    def _l10n_in_edi_generate_invoice_json(self, invoice):
        tax_details = self._l10n_in_prepare_edi_tax_details(invoice)
        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(invoice)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        is_intra_state = invoice.l10n_in_state_id == invoice.company_id.state_id
        is_overseas = invoice.l10n_in_gst_treatment == "overseas"
        lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section', 'rounding'))
        tax_details_per_record = tax_details.get("tax_details_per_record")
        json_payload = {
            "Version": "1.1",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": self._l10n_in_get_supply_type(invoice, tax_details_by_code),
                "RegRev": tax_details_by_code.get("is_reverse_charge") and "Y" or "N",
                "IgstOnIntra": is_intra_state and tax_details_by_code.get("igst") and "Y" or "N"},
            "DocDtls": {
                "Typ": invoice.move_type == "out_refund" and "CRN" or "INV",
                "No": invoice.name,
                "Dt": invoice.invoice_date.strftime("%d/%m/%Y")},
            "SellerDtls": self._get_l10n_in_edi_partner_details(saler_buyer.get("seller_details")),
            "BuyerDtls": self._get_l10n_in_edi_partner_details(
                saler_buyer.get("buyer_details"), pos_state_id=invoice.l10n_in_state_id, is_overseas=is_overseas),
            "ItemList": [
                self._get_l10n_in_edi_line_details(index, line, tax_details_per_record.get(line, {}))
                for index, line in enumerate(lines, start=1)
            ],
            "ValDtls": {
                "AssVal": self._l10n_in_round_value(tax_details.get("base_amount")),
                "CgstVal": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00)),
                "SgstVal": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00)),
                "IgstVal": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00)),
                "CesVal": self._l10n_in_round_value((
                    tax_details_by_code.get("cess_amount", 0.00)
                    + tax_details_by_code.get("cess_non_advol_amount", 0.00)),
                ),
                "StCesVal": self._l10n_in_round_value((
                    tax_details_by_code.get("state_cess_amount", 0.00)
                    + tax_details_by_code.get("state_cess_non_advol_amount", 0.00)),
                ),
                "RndOffAmt": self._l10n_in_round_value(
                    sum(line.balance for line in invoice.invoice_line_ids if line.display_type == 'rounding')),
                "TotInvVal": self._l10n_in_round_value(
                    (tax_details.get("base_amount") + tax_details.get("tax_amount"))),
            },
        }
        if invoice.company_currency_id != invoice.currency_id:
            json_payload["ValDtls"].update({
                "TotInvValFc": self._l10n_in_round_value(
                    (tax_details.get("base_amount_currency") + tax_details.get("tax_amount_currency")))
            })
        if saler_buyer.get("seller_details") != saler_buyer.get("dispatch_details"):
            json_payload.update({
                "DispDtls": self._get_l10n_in_edi_partner_details(saler_buyer.get("dispatch_details"),
                    set_vat=False, set_phone_and_email=False)
            })
        if saler_buyer.get("buyer_details") != saler_buyer.get("ship_to_details"):
            json_payload.update({
                "ShipDtls": self._get_l10n_in_edi_partner_details(saler_buyer.get("ship_to_details"), is_overseas=is_overseas)
            })
        if is_overseas:
            json_payload.update({
                "ExpDtls": {
                    "RefClm": tax_details_by_code.get("igst") and "Y" or "N",
                    "ForCur": invoice.currency_id.name,
                    "CntCode": saler_buyer.get("buyer_details").country_id.code or "",
                }
            })
            if invoice.l10n_in_shipping_bill_number:
                json_payload["ExpDtls"].update({
                    "ShipBNo": invoice.l10n_in_shipping_bill_number,
                })
            if invoice.l10n_in_shipping_bill_date:
                json_payload["ExpDtls"].update({
                    "ShipBDt": invoice.l10n_in_shipping_bill_date.strftime("%d/%m/%Y"),
                })
            if invoice.l10n_in_shipping_port_code_id:
                json_payload["ExpDtls"].update({
                    "Port": invoice.l10n_in_shipping_port_code_id.code
                })
        return json_payload

    @api.model
    def _l10n_in_prepare_edi_tax_details(self, move, in_foreign=False):
        def l10n_in_grouping_key_generator(base_line, tax_values):
            invl = base_line['record']
            tax = tax_values['tax_repartition_line'].tax_id
            tags = tax_values['tax_repartition_line'].tag_ids
            line_code = "other"
            if not invl.currency_id.is_zero(tax_values['tax_amount_currency']):
                if any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_cess")):
                    if tax.amount_type != "percent":
                        line_code = "cess_non_advol"
                    else:
                        line_code = "cess"
                elif any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_state_cess")):
                    if tax.amount_type != "percent":
                        line_code = "state_cess_non_advol"
                    else:
                        line_code = "state_cess"
                else:
                    for gst in ["cgst", "sgst", "igst"]:
                        if any(tag in tags for tag in self.env.ref("l10n_in.tax_tag_%s"%(gst))):
                            line_code = gst
            return {
                "tax": tax,
                "base_product_id": invl.product_id,
                "tax_product_id": invl.product_id,
                "base_product_uom_id": invl.product_uom_id,
                "tax_product_uom_id": invl.product_uom_id,
                "line_code": line_code,
            }

        def l10n_in_filter_to_apply(base_line, tax_values):
            if base_line['record'].display_type == 'rounding':
                return False
            return True

        return move._prepare_edi_tax_details(
            filter_to_apply=l10n_in_filter_to_apply,
            grouping_key_generator=l10n_in_grouping_key_generator,
        )

    @api.model
    def _get_l10n_in_tax_details_by_line_code(self, tax_details):
        l10n_in_tax_details = {}
        for tax_detail in tax_details.values():
            if tax_detail["tax"].l10n_in_reverse_charge:
                l10n_in_tax_details.setdefault("is_reverse_charge", True)
            l10n_in_tax_details.setdefault("%s_rate" % (tax_detail["line_code"]), tax_detail["tax"].amount)
            l10n_in_tax_details.setdefault("%s_amount" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details.setdefault("%s_amount_currency" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details["%s_amount" % (tax_detail["line_code"])] += tax_detail["tax_amount"]
            l10n_in_tax_details["%s_amount_currency" % (tax_detail["line_code"])] += tax_detail["tax_amount_currency"]
        return l10n_in_tax_details

    def _l10n_in_get_supply_type(self, move, tax_details_by_code):
        supply_type = "B2B"
        if move.l10n_in_gst_treatment in ("overseas", "special_economic_zone") and tax_details_by_code.get("igst_amount"):
            supply_type = move.l10n_in_gst_treatment == "overseas" and "EXPWP" or "SEZWP"
        elif move.l10n_in_gst_treatment in ("overseas", "special_economic_zone"):
            supply_type = move.l10n_in_gst_treatment == "overseas" and "EXPWOP" or "SEZWOP"
        elif move.l10n_in_gst_treatment == "deemed_export":
            supply_type = "DEXP"
        return supply_type

    #================================ API methods ===========================

    @api.model
    def _l10n_in_edi_no_config_response(self):
        return {'error': [{
            'code': '000',
            'message': _(
                "A username and password still needs to be set or it's wrong for the E-invoice(IN). "
                "It needs to be added and verify in the Settings."
            )}
        ]}

    @api.model
    def _l10n_in_edi_get_token(self, company):
        sudo_company = company.sudo()
        if sudo_company.l10n_in_edi_username and sudo_company._l10n_in_edi_token_is_valid():
            return sudo_company.l10n_in_edi_token
        elif sudo_company.l10n_in_edi_username and sudo_company.l10n_in_edi_password:
            self._l10n_in_edi_authenticate(company)
            return sudo_company.l10n_in_edi_token
        return False

    @api.model
    def _l10n_in_edi_connect_to_server(self, company, url_path, params):
        user_token = self.env["iap.account"].get("l10n_in_edi")
        params.update({
            "account_token": user_token.account_token,
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
            "username": company.sudo().l10n_in_edi_username,
            "gstin": company.vat,
        })
        if company.sudo().l10n_in_edi_production_env:
            default_endpoint = DEFAULT_IAP_ENDPOINT
        else:
            default_endpoint = DEFAULT_IAP_TEST_ENDPOINT
        endpoint = self.env["ir.config_parameter"].sudo().get_param("l10n_in_edi.endpoint", default_endpoint)
        url = "%s%s" % (endpoint, url_path)
        try:
            return jsonrpc(url, params=params, timeout=25)
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                "error": [{
                    "code": "404",
                    "message": _("Unable to connect to the online E-invoice service."
                        "The web service may be temporary down. Please try again in a moment.")
                }]
            }

    @api.model
    def _l10n_in_edi_authenticate(self, company):
        params = {"password": company.sudo().l10n_in_edi_password}
        response = self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/authenticate", params=params)
        # validity data-time in Indian standard time(UTC+05:30) so remove that gap and store in odoo
        if "data" in response:
            tz = pytz.timezone("Asia/Kolkata")
            local_time = tz.localize(fields.Datetime.to_datetime(response["data"]["TokenExpiry"]))
            utc_time = local_time.astimezone(pytz.utc)
            company.sudo().l10n_in_edi_token_validity = fields.Datetime.to_string(utc_time)
            company.sudo().l10n_in_edi_token = response["data"]["AuthToken"]
        return response

    @api.model
    def _l10n_in_edi_generate(self, company, json_payload):
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        params = {
            "auth_token": token,
            "json_payload": json_payload,
        }
        return self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/generate", params=params)

    @api.model
    def _l10n_in_edi_get_irn_by_details(self, company, json_payload):
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        params = {
            "auth_token": token,
        }
        params.update(json_payload)
        return self._l10n_in_edi_connect_to_server(
            company,
            url_path="/iap/l10n_in_edi/1/getirnbydocdetails",
            params=params,
        )

    @api.model
    def _l10n_in_edi_cancel(self, company, json_payload):
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        params = {
            "auth_token": token,
            "json_payload": json_payload,
        }
        return self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/cancel", params=params)
