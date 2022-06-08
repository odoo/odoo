# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
import pytz
import markupsafe
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.tools import html_escape
from odoo.exceptions import AccessError
from odoo.addons.iap import jsonrpc
import logging

_logger = logging.getLogger(__name__)

DEFAULT_IAP_ENDPOINT = "https://jva-odoo-iap-apps1.odoo.com"
DEFAULT_IAP_TEST_ENDPOINT = "https://jva-odoo-iap-apps1.odoo.com"


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code == "in_ewaybill_1_03":
            return journal.company_id.country_id.code == 'IN' and journal.type in ('sale', 'purchase')
        return super()._is_compatible_with_journal(journal)

    def _is_enabled_by_default_on_journal(self, journal):
        self.ensure_one()
        if self.code == "in_ewaybill_1_03":
            return journal.company_id.country_id.code == 'IN'
        return super()._is_enabled_by_default_on_journal(journal)

    def _is_required_for_invoice(self, invoice):
        self.ensure_one()
        if self.code == "in_ewaybill_1_03":
            product_types = invoice.mapped('invoice_line_ids.product_id.type')
            # only create if there is one or more goods.
            if 'consu' in product_types or 'product' in product_types:
                einvoice_in_edi_format = invoice.journal_id.edi_format_ids.filtered(lambda f: f.code == 'in_einvoice_1_03')
                return einvoice_in_edi_format and not einvoice_in_edi_format._is_required_for_invoice(invoice) or True
            else:
                return False
        return super()._is_required_for_invoice(invoice)

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == "in_ewaybill_1_03" or super()._needs_web_services()

    def _get_invoice_edi_content(self, move):
        if self.code != "in_ewaybill_1_03":
            return super()._get_invoice_edi_content(move)
        json_dump = json.dumps(self._l10n_in_edi_generate_irn_ewaybill_json(move))
        return json_dump.encode()

    def _check_move_configuration(self, move):
        if self.code != "in_ewaybill_1_03":
            return super()._check_move_configuration(move)
        error_message = []
        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(move)
        error_message += self._l10n_in_validate_partner(saler_buyer.get('dispatch_details'))
        error_message += self._l10n_in_validate_partner(saler_buyer.get('ship_to_details'))
        if not re.match("^.{1,16}$", move.name):
            error_message.append(_("Invoice number should not be more than 16 characters"))
        for line in move.invoice_line_ids.filtered(lambda line: not (line.display_type or line.is_rounding_line)):
            if line.product_id:
                hsn_code = self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code)
                if not hsn_code:
                    error_message.append(_("HSN code is not set in product %s", line.product_id.name))
                elif not re.match("^[0-9]+$", hsn_code):
                    error_message.append(_("Invalid HSN Code (%s) in product %s", hsn_code, line.product_id.name))
            else:
                error_message.append(_("product is required to get HSN code"))
        if not move.l10n_in_transaction_type:
            error_message.append(_("Transaction Type is required"))
        if not move.l10n_in_type_id:
            error_message.append(_("Document Type is required"))
        if not move.l10n_in_subtype_id:
            error_message.append(_("Sub Supply Type is required"))
        if not move.l10n_in_mode:
            error_message.append(_("Transportation Mode is required for E-waybill"))
        if move.l10n_in_mode == '0' and not self.l10n_in_transporter_id:
            error_message.append(_("Transporter is required when E-waybill is managed by transporter"))
        if move.l10n_in_mode == '1':
            if not move.l10n_in_vehicle_no:
                error_message.append(_("Vehicle Number is required when Transportation Mode is By Road"))
            if not move.l10n_in_vehicle_type:
                error_message.append(_("Vehicle Type is required when Transportation Mode is By Road"))
        if move.l10n_in_mode in ("2", "3", "4"):
            if not move.l10n_in_transportation_doc_no:
                error_message.append(_("Transport document number is required when Transportation Mode is Rail,Air or Ship"))
            if not move.l10n_in_transportation_doc_date:
                error_message.append(_("Transport document date is required when Transportation Mode is Rail,Air or Ship"))
        return error_message

    def _l10n_in_edi_ewaybill_get_iap_buy_credits_message(self, company):
        base_url = "https://iap-sandbox.odoo.com/iap/1/credit" if not company.sudo().l10n_in_edi_stock_production_env else ""
        url = self.env["iap.account"].get_credits_url(service_name="l10n_in_edi", base_url=base_url)
        return markupsafe.Markup("""<p><b>%s</b></p><p>%s</p>""" % (
            _("You have insufficient credits to send this document!"),
            _("Please proceed to buy more credits <a href='%s'>here.</a>", url),
        ))

    def _post_invoice_edi(self, invoices):
        if self.code != "in_ewaybill_1_03":
            return super()._post_invoice_edi(invoices)
        response = {}
        res = {}
        generate_json = self._l10n_in_edi_generate_ewaybill_json(invoices)
        response = self._l10n_in_edi_ewaybill_generate(invoices.company_id, generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                authenticate_response = self._l10n_in_edi_ewaybill_authenticate(invoices.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_ewaybill_generate(invoices.company_id, generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "604" in error_codes:
                get_ewaybill_response = self._get_l10n_in_edi_ewaybill_details_by_consigner(
                    invoices.company_id, generate_json.get('docType'), generate_json.get('docNo'))
                if not get_ewaybill_response.get("error"):
                    if generate_json.get('docDate') in get_ewaybill_response.get("data", {}).get('ewayBillDate', ''):
                        response = get_ewaybill_response
                        error_codes = []
                        error = []
                        invoices.message_post(body=_(
                            "Somehow this ewaybill had been submited to government before." \
                            "<br/>Normally, this should not happen too often" \
                            "<br/>Just verify value of ewaybill by fillup details on government website " \
                            "<a href='https://ewaybill2.nic.in/ewaybill_nat2/Others/EBPrintnew.aspx'>here<a>."
                        ))
            if "no-credit" in error_codes:
                res[invoices] = {
                    "success": False,
                    "error": self._l10n_in_edi_ewaybill_get_iap_buy_credits_message(invoices.company_id),
                    "blocking_level": "error",
                }
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                res[invoices] = {
                    "success": False,
                    "error": error_message,
                    "blocking_level": ("404" in error_codes) and "warning" or "error",
                }
        if not response.get("error"):
            response_data = response.get("data", {})
            json_dump = json.dumps(response_data)
            json_name = "%s_ewaybill_%s.json" % (
                invoices.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
            attachment = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "account.move",
                "res_id": invoices.id,
                "mimetype": "application/json",
            })
            inv_res = {"success": True, "attachment": attachment}
            if response_data.get('alert'):
                inv_res.update({'blocking_level': "info", "error": response_data['alert']})
            res[invoices] = inv_res
        return res

    def _cancel_invoice_edi(self, invoices):
        if self.code != "in_ewaybill_1_03":
            return super()._cancel_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            l10n_in_edi_ewaybill_response_json = invoice._get_l10n_in_edi_response_json()
            json_payload = {
                'ewbNo': int(l10n_in_edi_ewaybill_response_json.get('l10n_in_ewaybill_number')),
                'cancelRsnCode': int(invoice.l10n_in_edi_cancel_reason_code),
            }
            if invoice.l10n_in_edi_cancel_remarks:
                json_payload.update({'cancelRmrk': invoice.l10n_in_edi_cancel_remarks})
            response = self._l10n_in_edi_stock_cancel(invoice.company_id, json_payload)
            if response.get("error"):
                error = response["error"]
                error_codes = [e.get("code") for e in error]
                if "238" in error_codes:
                    authenticate_response = self._l10n_in_edi_stock_authenticate(invoice.company_id)
                    if not authenticate_response.get("error"):
                        error = []
                        response = self._l10n_in_edi_stock_cancel(invoice.company_id, json_payload)
                        if response.get("error"):
                            error = response["error"]
                            error_codes = [e.get("code") for e in error]
                if "no-credit" in error_codes:
                    res[invoices] = {
                        "success": False,
                        "error": self._l10n_in_edi_ewaybill_get_iap_buy_credits_message(invoices.company_id),
                        "blocking_level": "error",
                    }
                elif error:
                    error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                    res[invoices] = {
                        "success": False,
                        "error": error_message,
                        "blocking_level": ("404" in error_codes) and "warning" or "error",
                    }
            if not response.get("error"):
                json_dump = json.dumps(response.get("data"))
                json_name = "%s_cancel_ewaybill_%s.json" % (
                    invoice.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
                attachment = self.env["ir.attachment"].create({
                    "name": json_name,
                    "raw": json_dump.encode(),
                    "res_model": "account.move",
                    "res_id": invoice.id,
                    "mimetype": "application/json",
                })
                res[invoice] = {"success": True, "attachment": attachment}
        return res

    def _l10n_in_edi_generate_ewaybill_json(self, invoice):
        def filter_to_apply(tax_values):
            if tax_values["base_line_id"].is_rounding_line:
                return False
            if tax_values["base_line_id"].product_id.type == 'service':
                return False
            return True
        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(invoice)
        seller_details = saler_buyer.get('seller_details')
        dispatch_details = saler_buyer.get('dispatch_details')
        buyer_details = saler_buyer.get('buyer_details')
        ship_to_details = saler_buyer.get('ship_to_details')
        sign = invoice.is_inbound() and -1 or 1
        is_export = False
        is_import = False
        if invoice.l10n_in_gst_treatment == 'overseas':
            if invoice.is_purchase_document(include_receipts=True):
                is_import = True
            else:
                is_export = True
        extract_digits = self._l10n_in_edi_extract_digits
        tax_details = self._l10n_in_prepare_edi_tax_details(invoice, filter_to_apply)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        invoice_line_tax_details = tax_details.get("invoice_line_tax_details")
        json_payload = {
            "supplyType": ('in_' in invoice.move_type) and 'I' or 'O',
            "docNo": invoice.is_purchase_document(include_receipts=True) and invoice.ref or invoice.name,
            "docDate": invoice.date.strftime('%d/%m/%Y'),
            "fromGstin": not is_import and seller_details.commercial_partner_id.vat or 'URP',
            "fromTrdName": seller_details.commercial_partner_id.name,
            "fromStateCode": is_import and 99 or (int(invoice.l10n_in_state_id.l10n_in_tin)
                if ('in_' in invoice.move_type) and invoice.l10n_in_state_id else int(seller_details.state_id.l10n_in_tin)),
            "fromAddr1": dispatch_details.street or '',
            "fromAddr2": dispatch_details.street2 or '',
            "fromPlace": dispatch_details.city or '',
            "fromPincode": int(extract_digits(dispatch_details.zip)),
            "actFromStateCode": int(dispatch_details.state_id.l10n_in_tin),
            "toGstin": not is_export and buyer_details.commercial_partner_id.vat or 'URP',
            "toTrdName": buyer_details.commercial_partner_id.name,
            "toStateCode": is_export and 99 or (int(invoice.l10n_in_state_id.l10n_in_tin)
                if ('out_' in invoice.move_type) and invoice.l10n_in_state_id else int(buyer_details.state_id.l10n_in_tin)),
            "toAddr1": ship_to_details.street or '',
            "toAddr2": ship_to_details.street2 or '',
            "toPlace": ship_to_details.city or '',
            "toPincode": int(extract_digits(ship_to_details.zip)),
            "actToStateCode": int(ship_to_details.state_id.l10n_in_tin),
            "itemList": [
                self._get_l10n_in_edi_ewaybill_line_details(line, line_tax_details, sign)
                for line, line_tax_details in invoice_line_tax_details.items()
            ],
            "totalValue": self._l10n_in_round_value(tax_details.get("base_amount") * sign),
            "cgstValue": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00) * sign),
            "sgstValue": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00) * sign),
            "igstValue": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00) * sign),
            "cessValue": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00) * sign),
            "cessNonAdvolValue": self._l10n_in_round_value(tax_details_by_code.get("cess_non_advol_amount", 0.00) * sign),
            "otherValue": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00) * sign),
            "totInvValue": self._l10n_in_round_value((tax_details.get("base_amount") + tax_details.get("tax_amount")) * sign),
            "subSupplyType": invoice.l10n_in_subtype_id.code,
            "docType": invoice.l10n_in_type_id.code,
            "transactionType": int(invoice.l10n_in_transaction_type),
            "transDistance": str(invoice.l10n_in_distance or 0),
            'transMode': invoice.l10n_in_mode if invoice.l10n_in_mode != "0" else '',
            'transDocNo': invoice.l10n_in_transporter_doc_no if invoice.l10n_in_mode in ('2', '3', '4') else '',
            'vehicleNo': invoice.l10n_in_vehicle_no if invoice.l10n_in_mode == "1" else '',
        }
        if invoice.l10n_in_mode == '0':
            json_payload.update({'transporterId': invoice.l10n_in_transporter_id.vat})
        if invoice.l10n_in_mode == '0' and invoice.l10n_in_transporter_id:
            json_payload.update({'transporterName': invoice.l10n_in_transporter_id.name})
        if invoice.l10n_in_mode in ('2', '3', '4') and invoice.l10n_in_transporter_doc_date:
            json_payload.update({'transDocDate': invoice.l10n_in_transporter_doc_date.strftime('%d/%m/%Y')})
        if invoice.l10n_in_mode == '1' and invoice.l10n_in_vehicle_type:
            json_payload.update({'vehicleType': invoice.l10n_in_vehicle_type})
        return json_payload

    def _get_l10n_in_edi_ewaybill_line_details(self, line, line_tax_details, sign):
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(
            line_tax_details.get("tax_details", {}))
        line_details = {
            "productName": line.product_id.name,
            "hsnCode": line.product_id.l10n_in_hsn_code,
            "productDesc": line.name,
            "quantity": line.quantity,
            "qtyUnit": line.product_id.uom_id.l10n_in_code and line.product_id.uom_id.l10n_in_code.split('-')[0] or 'OTH',
            "taxableAmount": self._l10n_in_round_value(line.balance * sign),
        }
        if tax_details_by_code.get("igst_rate"):
            line_details.update({"igstRate": self._l10n_in_round_value(tax_details_by_code["igst_rate"])})
        else:
            line_details.update({
                "cgstRate": self._l10n_in_round_value(tax_details_by_code.get("cgst_rate", 0.00)),
                "sgstRate": self._l10n_in_round_value(tax_details_by_code.get("sgst_rate", 0.00)),
            })
        if tax_details_by_code.get("cess_rate"):
            line_details.update({"cessRate": self._l10n_in_round_value(tax_details_by_code.get("cess_rate"))})
        return line_details

    #================================ API methods ===========================

    @api.model
    def _l10n_in_edi_ewaybill_no_config_response(self):
        return {'error': [{
            'code': '000',
            'message': _(
                "A username and password still needs to be set or it's wrong for the E-WayBill(IN). "
                "It needs to be added and verify in the Settings."
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
            return jsonrpc(url, params=params, timeout=25)
        except AccessError as e:
            _logger.warning("Connection error: %s", e.args[0])
            return {
                "error": [{
                    "code": "404",
                    "message": _("Unable to connect to the online E-WayBill service."
                        "The web service may be temporary down. Please try again in a moment.")
                }]
            }

    @api.model
    def _l10n_in_edi_ewaybill_authenticate(self, company):
        params = {"password": company.sudo().l10n_in_edi_ewaybill_password}
        response = self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/authenticate", params=params
        )
        if response and response.get("status_cd") == '1':
            company.sudo().l10n_in_edi_ewaybill_auth_validity = fields.Datetime.now() + timedelta(
                hours=6, minutes=00, seconds=00)
            self.env.cr.commit()
        return response

    @api.model
    def _l10n_in_edi_ewaybill_generate(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/generate", params=params
        )

    @api.model
    def _l10n_in_edi_ewaybill_cancel(self, company, json_payload):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_ewaybill_no_config_response()
        params = {"json_payload": json_payload}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/cancel", params=params
        )

    @api.model
    def _get_l10n_in_edi_ewaybill_details_by_consigner(self, company, document_type, document_number):
        is_authenticated = self._l10n_in_edi_ewaybill_check_authentication(company)
        if not is_authenticated:
            return self._l10n_in_edi_stock_no_config_response()
        params = {"document_type": document_type, "document_number": document_number}
        return self._l10n_in_edi_ewaybill_connect_to_server(
            company, url_path="/iap/l10n_in_edi_stock/1/getewaybillgeneratedbyconsigner", params=params
        )
