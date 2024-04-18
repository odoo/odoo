from odoo import models, fields, api


class Evaluacion360(models.Model):
    _name = "evaluacion_360"
    _description = "Evaluaciones 360"

    _inherit = ["evaluacion"]

    @api.onchange('competencia_ids')
    def _onchange_competencia_ids(self):
        if self.competencia_ids:
            competencia_preguntas = self.competencia_ids.mapped('pregunta_ids')
            self.pregunta_ids = competencia_preguntas
        else:
            self.pregunta_ids = False

    pregunta_ids = fields.Many2many(
        'pregunta', relation='evaluacion_pregunta_rel', string='Preguntas')
    
    competencia_ids = fields.Many2many(
        'competencia', relation='evaluacion_competencia_rel', string='Competencias')
    
    usuario_ids = fields.Many2many(
        'res.users', relation='evaluacion_usuario_rel', string='Usuarios')
    
    
    
    
