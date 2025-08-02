from odoo import fields, models


class ShipperRateLine(models.TransientModel):
    _name = "shipper.rate.line"
    _description = "Shipping Rate Line"

    wizard_id = fields.Many2one('choose.delivery.carrier', string="Wizard", required=True, ondelete="cascade")
    carrier_name = fields.Char(string="Carrier")
    service = fields.Char(string="Service")
    final_price = fields.Float(string="Price")
    delivery_time = fields.Char(string="Delivery Time")
    logo_url = fields.Char(string="Logo URL")
    rate_id = fields.Integer(string="Rate ID")
    must_use_insurance = fields.Boolean(string="Must Use Insurance")
    insurance_fee = fields.Float(string="Insurance Fee")
    is_selected = fields.Boolean(string="Use")
