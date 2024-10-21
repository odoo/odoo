from odoo import fields, models


class Estate(models.Model):
    _name = "estate.estate"
    _description = "This is the estate model."

    status = fields.Char()
    price = fields.Float()
    bed = fields.Integer()
    bath = fields.Integer()
    street = fields.Char()
    city = fields.Char()
    state = fields.Char()
    zip_code = fields.Char()
    house_size = fields.Float()