from odoo import _, api, fields, models


class ShipmentCategory(models.Model):
    _name = "shipment.category"
    _description = "Shipment Category"
    _rec_name = "name"

    name = fields.Char(required=True)


class Shipment(models.Model):
    _name = "shipment.shipment"
    _inherit = ["mail.thread"]
    _description = "Shipment"
    _rec_name = "sequence_code"

    sequence_code = fields.Char(
        string="Shipment Code", required=True, copy=False, readonly=True, default="New"
    )
    sender_id = fields.Many2one("res.partner", string="Sender", required=True)
    receiver_name = fields.Char(string="Receiver Name", required=True)
    location = fields.Char(string="Location", required=True)
    parcel_type = fields.Selection(
        [("document", "Document"), ("parcel", "Parcel"), ("fragile", "Fragile"), ("other", "Other")],
        string="Parcel Type",
        required=True,
    )
    parcel_value = fields.Float(string="Parcel Value", required=True)
    name = fields.Char(string="Description", tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company", default=lambda self: self.env.company
    )
    for_sale = fields.Boolean(compute="_compute_for_sale", store=True)
    currency_id = fields.Many2one("res.currency", tracking=True)
    state = fields.Selection(
        [("new", "New"), ("in_transit", "In Transit"), ("delivered", "Delivered"), ("cancelled", "Cancelled")],
        default="new",
        tracking=True,
    )
    price = fields.Float(default=0.0, tracking=True)
    country_id = fields.Many2one("res.country")
    room_quantity = fields.Integer(default=1)
    image = fields.Binary(attachment=True)
    description = fields.Html()
    date_availability = fields.Date()
    owners_ids = fields.Many2many("res.partner")
    shipment_category_id = fields.Many2one("shipment.category")

    @api.model
    def create(self, vals):
        if vals.get("sequence_code", "New") == "New":
            vals["sequence_code"] = self.env["ir.sequence"].next_by_code("shipment.shipment") or "New"
        return super().create(vals)

    @api.depends("state")
    def _compute_for_sale(self):
        for shipment in self:
            shipment.for_sale = shipment.state in ["new", "in_transit"]

    @api.constrains("price")
    def _check_price(self):
        for shipment in self:
            if shipment.price < 0:
                raise models.ValidationError(_("Price cannot be negative"))

    def unlink(self):
        for shipment in self:
            if shipment.state == "delivered":
                raise models.ValidationError(_("Cannot delete a shipment that is delivered"))
        return super().unlink()
