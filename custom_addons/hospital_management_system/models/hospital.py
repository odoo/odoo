from odoo import models, fields

class Hospital(models.Model):
    _name = 'hospital.patient'

    name = field.Many2one('res.partner', string='patient')
    patient_id = fields.Integer(string='Patient')
    division = fields.Char(string='Division')