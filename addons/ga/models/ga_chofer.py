from odoo import fields, models
class Chofer(models.Model):

    _inherit = "hr.employee"

    is_chofer = fields.Boolean(string="Es Chofer")
    