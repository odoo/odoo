from odoo import fields, models


class EstateCategory(models.Model):
    _name = "shipment.category"
    _description = "EP Shipment Category"
    _rec_name = "name"

    name = fields.Char(required=True)
