# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError


class L10nInEwaybillExtend(models.TransientModel):
    _name = 'l10n.in.ewaybill.extend'
    _description = 'Extend validity of Ewaybill'

    l10n_in_ewaybill_id = fields.Many2one('l10n.in.ewaybill', string='Ewaybill', required=True)
    extension_reason_code = fields.Selection(
        selection=[
            ('1', 'Natural Calamity'),
            ('2', 'Law and Order Situation'),
            ('3', 'Transshipment'),
            ('4', 'Accident'),
            ('5', 'Others'),
        ],
        string="Reason for Extension",
        required=True,
    )
    extension_remarks = fields.Char("Extension Remarks")

    from_pincode = fields.Char(string="Current Pincode", required=True)
    from_state = fields.Many2one('res.country.state', string="Current State", required=True, domain="[('country_id.code', '=', 'IN')]")
    from_place = fields.Char(string="Current Place", required=True)
    remaining_distance = fields.Integer(string="Approximate Distance (In KM)", required=True)

    consignment_status = fields.Selection([
        ('T', 'In Transit'),
        ('M', 'In Movement'),
    ], string="Consignment is", required=True, default='M')
    trans_mode = fields.Selection([
        ('1', "Road"),
        ('2', "Rail"),
        ('3', "Air"),
        ('4', "Ship or Ship Cum Road/Rail"),
    ], string="Transport Mode", default='1')
    transit_type = fields.Selection([
        ('R', 'Road'),
        ('W', 'Warehouse'),
        ('O', 'Others'),
    ], string="Transit Type", default='R')

    vehicle_no = fields.Char("Vehicle Number")
    trans_doc_no = fields.Char("Transporter Doc No")
    trans_doc_date = fields.Date("Transporter Doc Date")

    def extend_ewaybill(self):
        self.ensure_one()
        if self.remaining_distance > self.l10n_in_ewaybill_id.distance:
            raise UserError(
                self.env._("Remaining distance should not be more then actual distance"),
            )
        payload = {
            "ewbNo": int(self.l10n_in_ewaybill_id.name),
            "vehicleNo": self.vehicle_no or "",
            "fromPlace": self.from_place,
            "fromState": int(self.from_state.l10n_in_tin),
            "remainingDistance": self.remaining_distance,
            "transDocNo": self.trans_doc_no or "",
            "transDocDate": self.trans_doc_date or "",
            "transMode": self.trans_mode if self.consignment_status == 'M' else "5",
            # transMode '5' states to InTransit mode, which should be passed if consignment_status is In transit.
            "transitType": "" if self.consignment_status == 'M' else self.transit_type,
            "extnRsnCode": int(self.extension_reason_code),
            "extnRemarks": self.extension_remarks or "",
            "fromPincode": int(self.from_pincode.strip()),
            "consignmentStatus": self.consignment_status,
        }
        self.l10n_in_ewaybill_id._ewaybill_extend(payload)
