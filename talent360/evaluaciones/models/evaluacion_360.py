from odoo import models, fields, api


class Evaluacion360(models.Model):
    _name = "evaluacion"
    _description = "Evaluaciones 360"

    _inherit = ["evaluacion"]

    @api.onchange('competencia_ids')
    def _onchange_competencia_ids(self):
        if self.tipo == 'NOM_035' or self.tipo == 'CLIMA':
            return
        if self.competencia_ids:
            competencia_preguntas = self.competencia_ids.mapped('pregunta_ids')
            self.pregunta_ids = competencia_preguntas
        else:
            self.pregunta_ids = False
