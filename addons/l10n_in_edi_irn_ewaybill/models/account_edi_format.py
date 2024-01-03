# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models, api, _
from odoo.tools import html_escape


class AccountEdiFormat(models.Model):
    _inherit = "account.edi.format"

    def _l10n_in_edi_ewaybill_base(self, move):
        """
            There is two type of api call to create E-waybill
            1. base on IRN, IRN is number created when we do E-invoice
            2. direct call, when E-invoice not aplicable or it"s credit note
        """
        einvoice_in_edi_format = move.journal_id.edi_format_ids.filtered(lambda f: f.code == "in_einvoice_1_03")
        if move.move_type != 'out_refund' and einvoice_in_edi_format and einvoice_in_edi_format._get_move_applicability(move):
            return "irn"
        return super()._l10n_in_edi_ewaybill_base(move)

    def _get_move_applicability(self, invoice):
        self.ensure_one()
        if self.code != 'in_ewaybill_1_03':
            return super()._get_move_applicability(invoice)

        res = super()._get_move_applicability(invoice)
        base = self._l10n_in_edi_ewaybill_base(invoice)
        if invoice.is_invoice() and invoice.country_code == 'IN' and base == 'irn':
            res.update({
                'post': self._l10n_in_edi_ewaybill_irn_post_invoice_edi,
                'edi_content': self._l10n_in_edi_ewaybill_irn_json_invoice_content,
            })
        return res

    def _l10n_in_edi_ewaybill_irn_json_invoice_content(self, move):
        return json.dumps(self._l10n_in_edi_irn_ewaybill_generate_json(move)).encode()

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
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message") or self._l10n_in_edi_ewaybill_get_error_message(e.get('code')))) for e in error])
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
