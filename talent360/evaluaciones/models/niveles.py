from odoo import models, fields

class Niveles(models.Model):

    _name = "niveles"
    _description = "Niveles de semaforización"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
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
            ("blanco", "Blanco"),
        ],
        required=True,
        string="Color",
    )