from odoo import models, fields


class Respuesta(models.Model):
    _name = "respuesta"
    _description = "Respuesta a una pregunta"

    pregunta_id = fields.One2many("pregunta", "respuesta_ids", string="Pregunta")
    user_id = fields.Many2one("res.users", string="Usuario")

    respuesta_texto = fields.Char("Respuesta", required=True)

