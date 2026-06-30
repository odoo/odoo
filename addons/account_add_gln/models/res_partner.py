from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    global_location_number = fields.Char(string="GLN", help="Global Location Number")
