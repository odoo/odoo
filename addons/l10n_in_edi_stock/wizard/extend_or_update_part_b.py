# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import pytz

from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape


class L10nInEDIStockExtendUpdatePartB(models.TransientModel):
    _name = "l10n.in.edi.stock.extend.update.partb"
    _description = "Extend or Update Part-B"

    request_type = fields.Selection(
        [
            ('extend', 'Extend'),
            ('update_part_b', 'Update Part-B'),
            ('update_transporter', 'Update Transporter ID')
        ], "Request Type", required=True)
    street = fields.Char("Street")
    street2 = fields.Char("Street2")
    street3 = fields.Char("Street3")
    from_place = fields.Char("From Place")
    from_state_id = fields.Many2one(
        "res.country.state",
        "Current State",
        domain=[("country_id.code", "=", "IN")]
    )
    from_pincode = fields.Char("Current Pincode")
    remaining_distance = fields.Char("Remaining Distance")
    extend_reason_code = fields.Selection(
        [
            ("1", "Natural Calamity"),
            ("2", "Law and Order Situation"),
            ("4", "Transhipment"),
            ("5", "Accident"),
            ("99", "Other")
        ],
        "Extend Reason"
    )
    remarks = fields.Char("Remarks")
    consignment_status = fields.Selection([("M", "In Movement"), ("T", "In Transit")], "Consignment Status")
    transit_type = fields.Selection([("R", "Road"), ("W", "Warehouse"), ("O", "Others")], "Transit Type")
    mode = fields.Selection(
        [
            ("1", "Road"),
            ("2", "Rail"),
            ("3", "Air"),
            ("4", "Ship")
        ],
        "Transportation Mode"
    )
    vehicle_no = fields.Char("Vehicle No")
    transporter_doc_no = fields.Char(
        "Document No",
        help="""Transporter document number.
If it is more than 15 chars, last 15 chars may be entered"""
    )
    transporter_doc_date = fields.Date("Document Date")
    update_reason_code = fields.Selection(
        [
            ("1", "Due to Break Down"),
            ("2", "Due to Transhipment"),
            ("3", "Others"),
            ("4", "First Time")
        ],
        "Reason"
    )
    transporter_id = fields.Many2one("res.partner", "Transporter")

    def action_process_ewaybill_request(self):
        self.ensure_one()
        picking_id = self.env['stock.picking'].browse(self._context.get('picking_id'))
        json_payload = {"ewbNo": int(picking_id.l10n_in_ewaybill_number)}
        if self.request_type == "extend":
            self._process_extend_ewaybill_request(picking_id, json_payload)
        elif self.request_type == "update_part_b":
            self._process_update_part_b_ewaybill_request(picking_id, json_payload)
        elif self.request_type == "update_transporter":
            self._process_update_transporter_ewaybill_request(picking_id, json_payload)

    def _process_extend_ewaybill_request(self, picking_id, json_payload):
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        json_payload.update({
            "fromPlace": self.from_place,
            "fromState": int(self.from_state_id.l10n_in_tin),
            "fromPincode": int(self.from_pincode),
            "remainingDistance": int(self.remaining_distance),
            "extnRsnCode": int(self.extend_reason_code),
            "extnRemarks": self.remarks,
            "consignmentStatus": self.consignment_status,
        })
        if self.consignment_status == "M" and self.mode == "1":
            json_payload.update({"transMode": self.mode, "vehicleNo": self.vehicle_no})
        elif self.consignment_status == "M" and self.mode in ("2", "3", "4"):
            json_payload.update({
                "transMode": self.mode,
                "transDocNo": self.transporter_doc_no,
                "transDocDate": self.transporter_doc_date.strftime('%d/%m/%Y')
            })
        elif self.consignment_status == "T":
            json_payload.update({
                "transMode": "5",
                "transitType": self.transit_type,
                "addressLine1": self.street,
                "addressLine2": self.street2,
                "addressLine3": self.street3
            })
        response = picking_obj._l10n_in_edi_stock_extend(picking_id.company_id, json_payload)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                authenticate_response = picking_obj._l10n_in_edi_stock_authenticate(picking_id.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = picking_obj._l10n_in_edi_stock_extend(picking_id.company_id, json_payload)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                raise UserError(_('%s', picking_obj._l10n_in_edi_stock_get_iap_buy_credits_message(picking_id.company_id)))
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                raise UserError(_('%s', error_message))
        if not response.get("error"):
            response_data = response.get("data")
            json_dump = json.dumps(response_data)
            json_name = "%s_extend_ewaybill_%s.json" % (
                picking_id.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
            attachment_id = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "stock.picking",
                "res_id": picking_id.id,
                "mimetype": "application/json",
            })
            tz = pytz.timezone("Asia/Kolkata")
            local_time = tz.localize(datetime.strptime(response_data.get("validUpto"), "%d/%m/%Y %H:%M:%S %p"))
            utc_time = local_time.astimezone(pytz.utc)
            picking_id.write({"l10n_in_ewaybill_valid_upto": fields.Datetime.to_string(utc_time)})
            body = _("E-Waybill Extended:<br/>EWaybill Valid Upto: %s") % (fields.Datetime.to_string(utc_time))
            picking_id.message_post(body=body, attachment_ids=[attachment_id.id])

    def _process_update_part_b_ewaybill_request(self, picking_id, json_payload):
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        json_payload.update({
            "reasonCode": self.update_reason_code,
            "reasonRem": self.remarks,
            "fromPlace": self.from_place,
            "fromState": int(self.from_state_id.l10n_in_tin),
            "transMode": self.mode,
        })
        if self.mode == "1":
            json_payload.update({"vehicleNo": self.vehicle_no})
        elif self.mode in ("2", "3", "4"):
            json_payload.update({
                "transDocNo": self.transporter_doc_no,
                "transDocDate": self.transporter_doc_date.strftime('%d/%m/%Y')
            })
        response = picking_obj._l10n_in_edi_stock_update_part_b(picking_id.company_id, json_payload)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                authenticate_response = picking_obj._l10n_in_edi_stock_authenticate(picking_id.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = picking_obj._l10n_in_edi_stock_update_part_b(picking_id.company_id, json_payload)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                raise UserError(_('%s', picking_obj._l10n_in_edi_stock_get_iap_buy_credits_message(picking_id.company_id)))
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                raise UserError(_('%s', error_message))
        if not response.get("error"):
            response_data = response.get("data")
            json_dump = json.dumps(response_data)
            json_name = "%s_update_part_b_ewaybill_%s.json" % (
                picking_id.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
            attachment_id = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "stock.picking",
                "res_id": picking_id.id,
                "mimetype": "application/json",
            })
            tz = pytz.timezone("Asia/Kolkata")
            local_time = tz.localize(datetime.strptime(response_data.get("validUpto"), "%d/%m/%Y %H:%M:%S %p"))
            utc_time = local_time.astimezone(pytz.utc)
            value = {"l10n_in_ewaybill_valid_upto": fields.Datetime.to_string(utc_time), "l10n_in_mode": self.mode}
            body = _("E-Waybill Updated Part-B:<br/>")
            if self.mode == "1":
                value.update({"l10n_in_vehicle_no": self.vehicle_no})
                body += _("Vehicle No: %s") % (self.vehicle_no)
            elif self.mode in ("2", "3", "4"):
                value.update({
                    "l10n_in_transporter_doc_no": self.transporter_doc_no,
                    "l10n_in_transporter_doc_date": self.transporter_doc_date
                })
                body += _("Document No: %s<br/>Document Date: %s") % (
                    self.transporter_doc_no, self.transporter_doc_date)
            picking_id.write(value)
            picking_id.message_post(body=body, attachment_ids=[attachment_id.id])

    def _process_update_transporter_ewaybill_request(self, picking_id, json_payload):
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        json_payload.update({"transporterId": self.transporter_id.vat})
        response = picking_obj._l10n_in_edi_stock_update_transporter(picking_id.company_id, json_payload)
        if response.get("error"):
            error = response["error"]
            error_codes = [e.get("code") for e in error]
            if "238" in error_codes:
                authenticate_response = picking_obj._l10n_in_edi_stock_authenticate(picking_id.company_id)
                if not authenticate_response.get("error"):
                    error = []
                    response = picking_obj._l10n_in_edi_stock_update_transporter(picking_id.company_id, json_payload)
                    if response.get("error"):
                        error = response["error"]
                        error_codes = [e.get("code") for e in error]
            if "no-credit" in error_codes:
                raise UserError(_('%s', picking_obj._l10n_in_edi_stock_get_iap_buy_credits_message(picking_id.company_id)))
            elif error:
                error_message = "<br/>".join(["[%s] %s" % (e.get("code"), html_escape(e.get("message"))) for e in error])
                raise UserError(_('%s', error_message))
        if not response.get("error"):
            response_data = response.get("data")
            json_dump = json.dumps(response_data)
            json_name = "%s_update_transporter_ewaybill_%s.json" % (
                picking_id.name.replace("/", "_"), fields.Datetime.now().strftime('%d_%m_%y_%H_%M_%S'))
            attachment_id = self.env["ir.attachment"].create({
                "name": json_name,
                "raw": json_dump.encode(),
                "res_model": "stock.picking",
                "res_id": picking_id.id,
                "mimetype": "application/json",
            })
            picking_id.write({
                "l10n_in_mode": "0",
                "l10n_in_transporter_id": self.transporter_id.id,
                "l10n_in_ewaybill_valid_upto": False
            })
            body = _("E-Waybill Updated Transporter:<br/>Transporter ID: %s<br/>Transporter Name: %s") % (
                self.transporter_id.vat, self.transporter_id.name)
            picking_id.message_post(body=body, attachment_ids=[attachment_id.id])
