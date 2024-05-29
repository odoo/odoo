from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Niveles(models.Model):

    _name = "niveles"
    _description = "Niveles de semaforización"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluación")
    descripcion_nivel = fields.Char(string="Descripción", default="Muy malo")
    techo = fields.Integer(string="Ponderación", default=0)
    color = fields.Char(string="Color", default="red")