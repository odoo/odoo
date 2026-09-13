from odoo import fields, models


class LunchLocation(models.Model):
    _name = "lunch.location"
    _description = "Lunch Locations"

    name = fields.Char("Location Name", required=True)
    address = fields.Text()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
