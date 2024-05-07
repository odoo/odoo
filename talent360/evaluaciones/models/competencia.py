from odoo import models, fields


class Competencia(models.Model):
    _name = "competencia"
    _description = "Competencia a evaluar"

    nombre = fields.Char(required=True)
    descripcion = fields.Text("Descripción")

    pregunta_ids = fields.Many2many(
        "pregunta",
        string="Preguntas",
    )
