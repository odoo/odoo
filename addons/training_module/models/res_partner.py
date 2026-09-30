from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    training_code = fields.Char(string='Training Code')
