from odoo import fields, models

class Partners(models.Model):
    _inherit = 'res.partner'

    # related for backward compatibility with < 13.0
    image_medium = fields.Binary(string="Medium-sized image", related='avatar_128', store=False, readonly=True)
