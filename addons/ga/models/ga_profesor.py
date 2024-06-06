from odoo import fields, models
class Profesor(models.Model):
    _inherit="hr.employee"
    unidad_educativa_id = fields.Many2one("ga.unidad.educativa", string="Profesor")