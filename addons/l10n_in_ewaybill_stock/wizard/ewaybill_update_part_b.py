# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext

from markupsafe import Markup


class EwaybillUpdatePartB(models.TransientModel):
    """
    Update Part B of the ewaybill
    """
    _name = 'ewaybill.update.part.b'
    _description = 'Update Part B'

    ewaybill_id = fields.Many2one("l10n.in.ewaybill")
    update_reason_code = fields.Selection(selection=[
        ("1", "Due to Breakdown"),
        ("2", "Due to Transhipment"),
        ("3", "Others (Pls. Specify)"),
        ("4", "First Time"),
        ], string="Update Reason", required=True, copy=False)
    update_remarks = fields.Char("Update remarks", copy=False)
    update_place = fields.Char("Place Of Change", copy=False)
    update_state_id = fields.Many2one("res.country.state", string='State Of Change', copy=False, domain="[('country_id.code', '=', 'IN')]")

    mode = fields.Selection([
        ("1", "Road"),
        ("2", "Rail"),
        ("3", "Air"),
        ("4", "Ship")],
        string="Transportation Mode", compute="_compute_wizard_values", store=True, readonly=False)

    # Vehicle Number and Type required when transportation mode is By Road.
    vehicle_no = fields.Char("Vehicle Number", copy=False, compute="_compute_wizard_values", store=True, readonly=False)
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

    @api.depends('ewaybill_id')
    def _compute_wizard_values(self):
        self.mode = self.ewaybill_id.mode
        self.vehicle_no = self.ewaybill_id.vehicle_no
        self.vehicle_type = self.ewaybill_id.vehicle_type
        self.transportation_doc_no = self.ewaybill_id.transportation_doc_no
        self.transportation_doc_date = self.ewaybill_id.transportation_doc_date

    def update_part_b(self):
        update_vals = {
            'update_reason_code': self.update_reason_code,
            'update_remarks': self.update_remarks,
            'update_place': self.update_place,
            'update_state_id': self.update_state_id,
            'mode': self.mode,
            'vehicle_no': self.vehicle_no,
            'vehicle_type': self.vehicle_type,
            'transportation_doc_no': self.transportation_doc_no,
            'transportation_doc_date': self.transportation_doc_date,
        }
        res = self.ewaybill_id._l10n_in_ewaybill_update_part_b(self.ewaybill_id, update_vals)
        if res.get(self.ewaybill_id).get('success') is True:
            self.ewaybill_id.write({
                'mode': self.mode,
                'vehicle_no': self.vehicle_no,
                'vehicle_type': self.vehicle_type,
                'transportation_doc_no': self.transportation_doc_no,
                'transportation_doc_date': self.transportation_doc_date,
            })
            body = Markup("%(title)s<ul><li>Reason => %(update_remarks)s (%(update_reason_code)s) </li><li>Place => %(update_place)s </li><li>State => %(update_state_id)s </li></ul>") % {
                'title': _("Ewaybill Part-B Updated"),
                'update_reason_code': dict(self._fields['update_reason_code'].selection).get(self.update_reason_code),
                'update_remarks': self.update_remarks,
                'update_place': self.update_place,
                'update_state_id': self.update_state_id,
            }
            self.ewaybill_id.message_post(body=body)
        else:
            raise ValidationError(_("\nEwaybill Part-B not updated \n\n%s") % (html2plaintext(res.get(self.ewaybill_id).get("error", False))))
