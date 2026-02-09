from odoo import api, fields, models


class RamWebsiteGalleryImage(models.Model):
    _name = "ram.website.gallery.image"
    _description = "RAM Website Gallery Image"
    _inherit = ["website.published.multi.mixin", "image.mixin"]
    _order = "sequence asc, id desc"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    caption = fields.Char()

    @api.depends_context("lang")
    def _compute_website_url(self):
        for record in self:
            record.website_url = "#gallery"
