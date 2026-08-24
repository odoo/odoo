from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    citizen_id_number = fields.Char(string="Citizen ID Number")
