from odoo import models, fields

class UsuarioEvaluacionRel(models.Model):
    _name = "usuario.evaluacion.rel"
    _description = "Relación entre evaluacion y usuarios"

    evaluacion_id = fields.Many2one("evaluacion", string="Evaluacion")
    usuario_id = fields.Many2one("res.users", string="Usuario")
    contestada = fields.Boolean(string="Contestada", default=False)

    # Campos relacionados para acceder a atributos de evaluacion
    evaluacion_nombre = fields.Char(related="evaluacion_id.nombre", string="Nombre de Evaluación", readonly=True)
    evaluacion_estado = fields.Selection(related="evaluacion_id.estado", string="Estado de Evaluación", readonly=True)
    evaluacion_tipo = fields.Selection(related="evaluacion_id.tipo", string="Tipo de Evaluación", readonly=True)
