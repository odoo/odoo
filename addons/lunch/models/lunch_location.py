from odoo import fields, models


class LunchLocation(models.Model):
    _name = "lunch.location"
    _description = "Lunch Locations"

    name = fields.Char(
        string="Location Name",
        required=True,
    )
    address = fields.Text()
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
