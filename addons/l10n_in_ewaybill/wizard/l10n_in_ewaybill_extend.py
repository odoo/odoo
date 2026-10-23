# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class L10nInEwaybillExtend(models.TransientModel):
    _name = 'l10n.in.ewaybill.extend'
    _description = 'Extend validity of Ewaybill'

    l10n_in_ewaybill_id = fields.Many2one('l10n.in.ewaybill', string='Ewaybill', required=True)
    extension_reason_code = fields.Selection([
        ('1', 'Natural Calamity'),
        ('2', 'Law and Order Situation'),
        ('3', 'Transhipment'),
        ('4', 'Accident'),
        ('5', 'Others'),
    ], string="Reason for Extension", required=True)
    extension_remarks = fields.Char("Extension Remarks", required=True)

    from_pincode = fields.Char(string="Current Pincode", required=True)
    from_state_id = fields.Many2one('res.country.state', string="Current State", required=True, domain=[('country_id.code', '=', 'IN')])
    from_place = fields.Char(string="Current Place", required=True)
    address_line1 = fields.Char(string="Address Line 1")
    address_line2 = fields.Char(string="Address Line 2")
    address_line3 = fields.Char(string="Address Line 3")
    remaining_distance = fields.Integer(string="Approximate Distance (In KM)", required=True)

    consignment_status = fields.Selection(
        selection=[
            ('T', 'In Transit'),
            ('M', 'In Movement'),
        ],
        string="Consignment is",
        required=True, default='M',
    )
    trans_mode = fields.Selection(
        selection=[
            ('1', "Road"),
            ('2', "Rail"),
            ('3', "Air"),
            ('4', "Ship or Ship Cum Road/Rail"),
        ],
        string="Transport Mode",
        compute='_compute_transport_details', store=True, readonly=False,
    )
    transit_type = fields.Selection(
        selection=[
            ('R', 'Road'),
            ('W', 'Warehouse'),
            ('O', 'Others'),
        ],
        string="Transit Type", default='R',
    )

    vehicle_no = fields.Char(
        string="Vehicle Number",
        compute='_compute_transport_details', store=True, readonly=False,
    )
    trans_doc_no = fields.Char(
        string="Transporter Doc No",
        compute='_compute_transport_details', store=True, readonly=False,
    )
    trans_doc_date = fields.Date(
        string="Transporter Doc Date",
        compute='_compute_transport_details', store=True, readonly=False,
    )

    @api.depends('l10n_in_ewaybill_id')
    def _compute_transport_details(self):
        for wizard in self:
            ewaybill = wizard.l10n_in_ewaybill_id
            wizard.trans_mode = ewaybill.mode
            wizard.vehicle_no = ewaybill.vehicle_no
            wizard.trans_doc_no = ewaybill.transportation_doc_no
            wizard.trans_doc_date = ewaybill.transportation_doc_date

    def action_submit_extension(self):
        self.ensure_one()

        pincode = self.from_pincode.strip()
        if len(pincode) != 6 or not pincode.isdigit():
            raise UserError(self.env._("Please enter a valid 6-digit pincode."))
        in_movement = self.consignment_status == 'M'
        send_vehicle = (in_movement and self.trans_mode == '1') or (not in_movement and self.transit_type == 'R')
        send_trans_doc = not (in_movement and self.trans_mode == '1')
        payload = {
            "ewbNo": int(self.l10n_in_ewaybill_id.name),
            **({"vehicleNo": self.vehicle_no} if send_vehicle and self.vehicle_no else {}),
            "fromPlace": self.from_place,
            "fromState": int(self.from_state_id.l10n_in_tin),
            "remainingDistance": self.remaining_distance,
            **({"transDocNo": self.trans_doc_no} if send_trans_doc and self.trans_doc_no else {}),
            **({"transDocDate": self.trans_doc_date.strftime("%d/%m/%Y")} if send_trans_doc and self.trans_doc_date else {}),
            **({"transitType": self.transit_type} if not in_movement else {}),
            **({"addressLine1": self.address_line1} if self.address_line1 else {}),
            **({"addressLine2": self.address_line2} if self.address_line2 else {}),
            **({"addressLine3": self.address_line3} if self.address_line3 else {}),
            "transMode": self.trans_mode if in_movement else "5",
            # transMode '5' states to InTransit mode, which should be passed if consignment_status is In transit.
            "extnRsnCode": int(self.extension_reason_code),
            "extnRemarks": self.extension_remarks,
            "fromPincode": int(pincode),
            "consignmentStatus": self.consignment_status,
        }
        self.l10n_in_ewaybill_id._ewaybill_extend(payload)
