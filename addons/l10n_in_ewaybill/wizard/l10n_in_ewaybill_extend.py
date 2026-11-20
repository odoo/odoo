# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10nInEwaybillExtend(models.TransientModel):
    _name = 'l10n.in.ewaybill.extend'
    _description = 'Extend validity of Ewaybill'

    l10n_in_ewaybill_id = fields.Many2one('l10n.in.ewaybill', string='Ewaybill', required=True)
    use_partner_address = fields.Boolean(
        string="Use Existing Contact's Address?",
        help="Select this option to use an existing contact's address as the starting point for the transit location.",
    )
    from_partner_id = fields.Many2one(
        'res.partner',
        string="Transit Location (Partner)",
        help="Select the partner representing the location where the goods are currently in transit.",
    )
    extension_reason_code = fields.Selection([
        ('1', 'Natural Calamity'),
        ('2', 'Law and Order Situation'),
        ('3', 'Transhipment'),
        ('4', 'Accident'),
        ('5', 'Others'),
    ], string="Reason for Extension", required=True)
    extension_remarks = fields.Char("Extension Remarks", required=True)

    from_pincode = fields.Char(string="Current Pincode", required=True)
    from_state = fields.Many2one('res.country.state', string="Current State", required=True, ui_domain="[('country_id.code', '=', 'IN')]")
    from_place = fields.Char(string="Current Place", required=True)
    address_line1 = fields.Char(string="Address Line 1", compute='_compute_from_address', store=True, readonly=False)
    address_line2 = fields.Char(string="Address Line 2", compute='_compute_from_address', store=True, readonly=False)
    address_line3 = fields.Char(string="Address Line 3", compute='_compute_from_address', store=True, readonly=False)
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

    @api.depends('from_partner_id', 'consignment_status')
    def _compute_from_address(self):
        for wizard in self:
            if wizard.consignment_status == 'T' and (partner := wizard.from_partner_id):
                wizard.address_line1 = partner.street
                wizard.address_line2 = partner.street2
                wizard.address_line3 = partner.city
            else:
                wizard.address_line1 = wizard.address_line2 = wizard.address_line3 = False

    def action_submit_extension(self):
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
            **({"addressLine1": self.address_line1} if self.address_line1 else {}),
            **({"addressLine2": self.address_line2} if self.address_line2 else {}),
            **({"addressLine3": self.address_line3} if self.address_line3 else {}),
            "transMode": self.trans_mode if self.consignment_status == 'M' else "5",
            # transMode '5' states to InTransit mode, which should be passed if consignment_status is In transit.
            "extnRsnCode": int(self.extension_reason_code),
            "extnRemarks": self.extension_remarks,
            "fromPincode": int(self.from_pincode.strip()),
            "consignmentStatus": self.consignment_status,
        }
        self.l10n_in_ewaybill_id._ewaybill_extend(payload)
