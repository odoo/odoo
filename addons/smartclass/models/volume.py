from odoo import models, fields, api

class Volume(models.Model):
    _name = "smartclass.volume"
    _description = "Volume Calculator"

    name = fields.Char("Name", required=True)
    depth = fields.Float("Depth (m)")
    width = fields.Float("Width (m)")
    height = fields.Float("Height (m)")
    volume = fields.Float("Volume (m³)", compute="_compute_volume", store=True)
    category = fields.Selection(
        [("small", "Small"), ("medium", "Medium"), ("large", "Large")],
        string="Category",
        compute="_compute_category",
        store=True
    )

    @api.depends("depth", "width", "height")
    def _compute_volume(self):
        for rec in self:
            rec.volume = round(rec.depth * rec.width * rec.height, 2)

    @api.depends("volume")
    def _compute_category(self):
        for rec in self:
            if rec.volume <= 1:
                rec.category = "small"
            elif rec.volume <= 100:
                rec.category = "medium"
            else:
                rec.category = "large"
