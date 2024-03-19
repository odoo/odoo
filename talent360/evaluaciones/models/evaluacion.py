from odoo import models, fields


class Evaluacion(models.Model):
    _name = "evaluacion"
    _description = "Evaluacion de pesonal"

    nombre = fields.Char("Nombre", required=True)
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('publicado', 'Publicado'),
        ('finalizado', 'Finalizado')
    ], default='borrador', required=True)

    pregunta_ids = fields.Many2many(
        "pregunta", "pregunta_evaluacion_rel", "evaluacion_id", "pregunta_id", string="Preguntas")

    competencia_ids = fields.Many2many(
        "competencia", "competencia_evaluacion_rel", "evaluacion_id", "competencia_id", string="Competencias")

    usuario_ids = fields.Many2many(
        "res.users", "usuario_evaluacion_rel", "evaluacion_id", "usuario_id", string="Asignados")
