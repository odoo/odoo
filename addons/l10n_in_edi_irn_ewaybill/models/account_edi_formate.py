# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json
import pytz
import markupsafe

from odoo import models, fields, api, _
from odoo.tools import html_escape
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
        if self.code == "in_irn_ewaybill_1_03":
            return journal.company_id.country_id.code == 'IN'
        return super()._is_enabled_by_default_on_journal(journal)

    def _is_required_for_invoice(self, invoice):
        self.ensure_one()
        if self.code == "in_irn_ewaybill_1_03":
            product_types = invoice.mapped('invoice_line_ids.product_id.type')
            # only create if there is one or more goods.
            if 'consu' in product_types or 'product' in product_types:
                # depend on E-invoice
                einvoice_in_edi_format = invoice.journal_id.edi_format_ids.filtered(lambda f: f.code == 'in_einvoice_1_03')
                return einvoice_in_edi_format._is_required_for_invoice(invoice)
            else:
                return False
        return super()._is_required_for_invoice(invoice)

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == "in_irn_ewaybill_1_03" or super()._needs_web_services()

    def _get_invoice_edi_content(self, move):
        if self.code != "in_irn_ewaybill_1_03":
            return super()._get_invoice_edi_content(move)
        json_dump = json.dumps(self._l10n_in_edi_generate_irn_ewaybill_json(move))
        return json_dump.encode()

    def _check_move_configuration(self, move):
        if self.code != "in_irn_ewaybill_1_03":
            return super()._check_move_configuration(move)
        error_message = []
        if not move.l10n_in_mode:
            error_message.append(_("Transportation Mode is required for E-waybill"))
        if move.l10n_in_mode == '0' and not self.l10n_in_transporter_id:
            error_message.append(_("Transporter is required when E-waybill is managed by transporter"))
        if move.l10n_in_mode == '1':
            if not move.l10n_in_vehicle_no:
                error_message.append(_("Vehicle Number is required when Transportation Mode is By Road"))
            if not move.l10n_in_vehicle_type:
                error_message.append(_("Vehicle Type is required when Transportation Mode is By Road"))
        if move.l10n_in_mode in ("2","3","4"):
            if not move.l10n_in_transportation_doc_no:
                error_message.append(_("Transport document number is required when Transportation Mode is Rail,Air or Ship"))
            if not move.l10n_in_transportation_doc_date:
                error_message.append(_("Transport document date is required when Transportation Mode is Rail,Air or Ship"))
        return error_message

    def _post_invoice_edi(self, invoices):
        if self.code != "in_irn_ewaybill_1_03":
            return super()._post_invoice_edi(invoices)
        response = {}
        res = {}
        generate_json = self._l10n_in_edi_generate_irn_ewaybill_json(invoices)
        response = self._l10n_in_edi_generate_irn_ewaybill(invoices.company_id, generate_json)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "1005" in error_codes:
                # Invalid token eror then create new token and send generate request again.
                # This happen when authenticate called from another odoo instance with same credentials (like. Demo/Test)
                authenticate_response = self._l10n_in_edi_authenticate(invoices.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = self._l10n_in_edi_generate_irn_ewaybill(invoices.company_id, generate_json)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "2150" in error_codes:
                # Get IRN by details in case of IRN is already generated
                # this happens when timeout from the Government portal but IRN is generated
                response = self._l10n_in_edi_get_ewaybill_by_irn(invoices.company_id, {'irn': generate_json.get('Irn')})
                if not response.get("error"):
                    error = []
                    odoobot = self.env.ref("base.partner_root")
                    invoices.message_post(author_id=odoobot.id, body=_(
                        "Somehow this Ewaybill is generate in government portal before." \
                        "<br/>Normally, this should not happen too often" \
                        "<br/>Just verify value of invoice by enter details into government website " \
                        "<a href='https://ewaybillgst.gov.in/Others/EBPrintnew.aspx'>here<a>."
                    ))
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
            if response.get("Remarks"):
                inv_res.update({'blocking_level': "info", "error": response.get("Remarks")})
            res[invoices] = inv_res
        return res

    def _cancel_invoice_edi(self, invoices):
        if self.code != "in_irn_ewaybill_1_03":
            return super()._cancel_invoice_edi(invoices)
        res = {}
        for invoice in invoices:
            res[invoice] = {
                "success": True,
                "error": "You need to cancel E-waybill using government portal",
                "blocking_level": "info"
            }
        return res

    def _l10n_in_edi_generate_irn_ewaybill_json(self, invoice):
        json_payload = {
            "Irn": invoice._get_l10n_in_edi_response_json().get('Irn'),
            "Distance": invoice.l10n_in_distance,
        }
        if invoice.l10n_in_mode == '0':
            json_payload.update({
                "TransId": invoice.l10n_in_transporter_id.vat,
                "TransName": invoice.l10n_in_transporter_id.name,
            })

        elif invoice.l10n_in_mode == '1':
            json_payload.update({
                "TransMode": invoice.l10n_in_mode,
                "VehNo": invoice.l10n_in_vehicle_no,
                "VehType": invoice.l10n_in_vehicle_type,
            })
        if invoice.l10n_in_mode == ('2','3','4'):
            json_payload.update({
                "TransMode": invoice.l10n_in_mode,
                "TransDocDt": doc_date and doc_date.strftime('%d/%m/%Y') or False,
                "TransDocNo": invoice.l10n_in_transportation_doc_no,
            })
        return json_payload

    #================================ API methods ===========================

    @api.model
    def _l10n_in_edi_generate_irn_ewaybill(self, company, json_payload):
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        if not json_payload.get("Irn"):
            return {'error': [{
                'code': 'waiting',
                'message': _("waiting For IRN generation To create E-waybill")}
            ]}
        params = {
            "auth_token": token,
            "json_payload": json_payload,
        }
        return self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/generate_ewaybill_by_irn", params=params)

    @api.model
    def _l10n_in_edi_get_ewaybill_by_irn(self, company, irn):
        token = self._l10n_in_edi_get_token(company)
        if not token:
            return self._l10n_in_edi_no_config_response()
        params = {
            "auth_token": token,
            "irn": irn,
        }
        return self._l10n_in_edi_connect_to_server(company, url_path="/iap/l10n_in_edi/1/get_ewaybill_by_irn", params=params)
