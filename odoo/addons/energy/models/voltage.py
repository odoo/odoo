from odoo import models, fields

class Voltage(models.Model):
    _name = "voltage"
    _description = "Description of the Voltage model"

    name = fields.Char()
   
