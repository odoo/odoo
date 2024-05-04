from odoo import models, fields


class Opcion(models.Model):
    _name = "opcion"
    _description = "Opcion para una pregunta"

    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
    opcion_texto = fields.Char("Opción", required=True)
    valor = fields.Integer("Valor", required=True, default=0)
