from odoo import models, fields


class Respuesta(models.Model):
    _name = "respuesta"
    _description = "Respuesta a una pregunta"

    pregunta_id = fields.Many2one("pregunta", string="Preguntas")
    usuario_id = fields.Many2one("res.users", string="Usuario")
    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")

    respuesta_texto = fields.Char("Respuesta", required=True)

    
