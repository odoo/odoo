from odoo import api, fields, models


class RamWebsiteLocation(models.Model):
    _name = "ram.website.location"
    _description = "RAM Website Location"
    _inherit = ["website.published.multi.mixin"]
    _order = "sequence asc, id desc"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    address = fields.Text()
    phone = fields.Char()
    opening_hours = fields.Char(help="Example: Mon-Sun: 11am - 10pm")
    latitude = fields.Float()
    longitude = fields.Float()
    google_maps_url = fields.Char(string="Google Maps URL")
    image_1920 = fields.Image()

    @api.depends_context("lang")
    def _compute_website_url(self):
        for record in self:
            record.website_url = "#locations"

