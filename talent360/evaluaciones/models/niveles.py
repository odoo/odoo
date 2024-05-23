from os import POSIX_SPAWN_OPEN
from odoo import models, fields
from talent360.evaluaciones.models import evaluacion

class Niveles(models.Model):

    _name = "niveles"
    _description = "Niveles de semaforización"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    piso = fields.Integer(string="Piso")
    techo = fields.Integer(string="Techo")
    color = fields.Selection(
        [
            ("rojo", "Rojo"),
            ("amarillo", "Amarillo"),
            ("verde", "Verde"),
            ("azul", "Azul"),
            ("gris", "Gris"),
            ("naranja", "Naranja"),
            ("morado", "Morado"),
            ("cafe", "Café"),
            ("rosa", "Rosa"),
        ],
        required=True,
        string="Color",
    )