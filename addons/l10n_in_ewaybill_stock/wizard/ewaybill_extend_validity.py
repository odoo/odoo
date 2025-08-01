# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext

from markupsafe import Markup


class EwaybillExtendValidity(models.TransientModel):
    """
    Extend Validity of the ewaybill
    """
    _name = 'ewaybill.extend.validity'
    _description = 'Extend Validity'

    ewaybill_id = fields.Many2one("l10n.in.ewaybill")
    extend_reason_code = fields.Selection([
        ("1", "Natural Calamity"),
        ("2", "Law and order"),
        ("3", "Transhipment"),
        ("4", "Accident"),
        ("5", "Others")], string="Validity Extend Reason", required=True, copy=False)

    extend_reason_remarks = fields.Char("Validity Extend Remarks", copy=False)
    current_pincode = fields.Char("Current Pincode", copy=False)
    current_place = fields.Char("Current Place", copy=False)

    current_state_id = fields.Many2one(
        "res.country.state", string='Current State', copy=False, domain="[('country_id.code', '=', 'IN')]")
    rem_distance = fields.Integer("Remaining Distance", copy=False)
    consignment_status = fields.Selection([
        ("T", "In Transit"),
        ("M", "In Movement"),
    ], default="M")

    mode = fields.Selection([
        ("1", "Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", required=True, copy=False, compute="_compute_wizard_values", store=True, readonly=False)

    # Vehicle Number and Type required when transportation mode is By Road.
    vehicle_no = fields.Char("Vehicle Number", compute="_compute_wizard_values", store=True, copy=False, readonly=False)
    vehicle_type = fields.Selection([
        ("R", "Regular"),
        ("O", "ODC")],
        string="Vehicle Type", copy=False, compute="_compute_wizard_values", store=True, readonly=False)

    transportation_doc_no = fields.Char(
        string="Transportation Document Number",
        help="""Transport document number. If it is more than 15 chars, last 15 chars may be entered""",
        copy=False, compute="_compute_wizard_values", store=True, readonly=False)

    transportation_doc_date = fields.Date(
        string="Document Date",
        help="Date on the transporter document",
        copy=False, compute="_compute_wizard_values", store=True, readonly=False)

    transit_type = fields.Selection(selection=[
        ("R", "Road"),
        ("W", "Warehouse"),
        ("O", "Others"),
        ], string="Transit Type", default="R", copy=False)

    @api.depends('ewaybill_id')
    def _compute_wizard_values(self):
        self.mode = self.ewaybill_id.mode
        self.vehicle_no = self.ewaybill_id.vehicle_no
        self.vehicle_type = self.ewaybill_id.vehicle_type
        self.transportation_doc_no = self.ewaybill_id.transportation_doc_no
        self.transportation_doc_date = self.ewaybill_id.transportation_doc_date

    def extend_validity(self):
        extend_vals = {
            'extend_reason_code': self.extend_reason_code,
            'extend_reason_remarks': self.extend_reason_remarks,
            'current_pincode': self.current_pincode,
            'current_place': self.current_place,
            'current_state_id': self.current_state_id,
            'rem_distance': self.rem_distance,
            'consignment_status': self.consignment_status,
            'transit_type': self.transit_type,
            'mode': self.mode,
            'vehicle_no': self.vehicle_no,
            'vehicle_type': self.vehicle_type,
            'transportation_doc_no': self.transportation_doc_no,
            'transportation_doc_date': self.transportation_doc_date,
        }
        res = self.ewaybill_id._l10n_in_ewaybill_extend_validity(self.ewaybill_id, extend_vals)
        if res.get(self.ewaybill_id).get('success') is True:
            self.ewaybill_id.write({
                'mode': self.mode,
                'vehicle_no': self.vehicle_no,
                'vehicle_type': self.vehicle_type,
                'transportation_doc_no': self.transportation_doc_no,
                'transportation_doc_date': self.transportation_doc_date,
            })
            body = Markup("%(title)s<ul><li>Reason => %(extend_reason_remarks)s (%(extend_reason_code)s) </li><li>Pincode => %(current_pincode)s </li><li>Place => %(current_place)s </li><li>State => %(current_state_id)s </li><li>Distance => %(rem_distance)s </li><li>Consignment => %(consignment_status)s </li><li>Transit Type => %(transit_type)s </li></ul>") % {
                'title': _("Ewaybill Validity Extended"),
                'extend_reason_code': dict(self._fields['extend_reason_code'].selection).get(self.extend_reason_code),
                'extend_reason_remarks': self.extend_reason_remarks,
                'current_pincode': self.current_pincode,
                'current_place': self.current_place,
                'current_state_id': self.current_state_id.name,
                'rem_distance': self.rem_distance,
                'consignment_status': dict(self._fields['consignment_status'].selection).get(self.consignment_status),
                'transit_type': dict(self._fields['transit_type'].selection).get(self.transit_type) or "",
            }
            self.ewaybill_id.message_post(body=body)
        else:
            raise ValidationError(_("\nEwaybill Validity not extended \n\n%s") % (html2plaintext(res.get(self.ewaybill_id).get("error", False))))
