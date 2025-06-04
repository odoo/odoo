from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Restaurants table'

    menupro_id = fields.Char(string='MenuPro ID')