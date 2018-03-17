from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pid_type = fields.Selection([('passport', 'Passport'),
                                 ('national', 'National ID'),
                                 ('driver', "Driver's ID"), ],
                                string="ID Presented",)
    identification = fields.Char('Identification No.')
