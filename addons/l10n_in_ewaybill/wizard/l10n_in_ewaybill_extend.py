# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
        payload = {
            "ewbNo": int(self.l10n_in_ewaybill_id.name),
            **({"vehicleNo": self.vehicle_no} if self.vehicle_no else {}),
            "fromPlace": self.from_place,
            "fromState": int(self.from_state.l10n_in_tin),
            "remainingDistance": self.remaining_distance,
            **({"transDocNo": self.trans_doc_no} if self.trans_doc_no else {}),
            **({"transDocDate": self.trans_doc_date.strftime("%d/%m/%Y")} if self.trans_doc_date else {}),
            **({"transitType": self.transit_type} if self.consignment_status == 'T' else {}),
            "transMode": self.trans_mode if self.consignment_status == 'M' else "5",
            # transMode '5' states to InTransit mode, which should be passed if consignment_status is In transit.
            "extnRsnCode": int(self.extension_reason_code),
            "extnRemarks": self.extension_remarks,
            "fromPincode": int(self.from_pincode.strip()),
            "consignmentStatus": self.consignment_status,
        }
        self.l10n_in_ewaybill_id._ewaybill_extend(payload)
