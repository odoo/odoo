from odoo import models, fields


class Competencia(models.Model):
    _name = "competencia"
    _description = "Competencia a evaluar"

    nombre = fields.Char("Nombre", required=True)
    descripcion = fields.Text("Descripción")

    company_id = fields.Many2one("res.company", string="Compañía")

    pregunta_ids = fields.Many2many(
        "pregunta", "pregunta_competencia_rel", "competencia_id", "pregunta_id", string="Preguntas")
