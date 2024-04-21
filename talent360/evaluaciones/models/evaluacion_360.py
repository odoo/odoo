from odoo import models, fields, api


class Evaluacion360(models.Model):
    """
    Modelo para representar Evaluaciones 360.
    Hereda de 'evaluacion'.
    """
    _name = "evaluacion"
    _description = "Evaluaciones 360"

    _inherit = ["evaluacion"]

    @api.onchange('competencia_ids')
    def _onchange_competencia_ids(self):
        """
        Método que se ejecuta cuando cambian las competencias.

        Si el tipo de evaluación no es 'NOM_035' o 'CLIMA', y hay competencias seleccionadas,
        asigna las preguntas relacionadas con esas competencias a la evaluación.
        """
        if self.tipo == 'NOM_035' or self.tipo == 'CLIMA':
            return
        if self.competencia_ids:
            competencia_preguntas = self.competencia_ids.mapped('pregunta_ids')
            self.pregunta_ids = competencia_preguntas
        else:
            self.pregunta_ids = False
