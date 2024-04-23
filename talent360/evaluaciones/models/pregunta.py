from odoo import models, fields


class Pregunta(models.Model):
    _name = "pregunta"
    _description = "Pregunta para una evaluación"

    pregunta_texto = fields.Char("Pregunta", required=True)
    tipo = fields.Selection(
        [
            ("multiple_choice", "Opción múltiple"),
            ("open_question", "Abierta"),
            ("escala", "Escala"),
        ],
        default="multiple_choice",
        required=True,
    )

    company_id = fields.Many2one("res.company", string="Compañía")
    opcion_ids = fields.One2many("opcion", "pregunta_id", string="Opciones")
    respuesta_ids = fields.One2many("respuesta", "pregunta_id", string="Respuestas")
    competencia_ids = fields.Many2many("competencia", string="Competencias")

    def ver_respuestas(self):
        evaluacion_id = self._context.get("current_evaluacion_id")
        # Redirect to graph view of respuestas filtered by evaluacion_id and pregunta_id grouped by respuesta
        return {
            "type": "ir.actions.act_window",
            "name": "Respuestas",
            "res_model": "respuesta",
            "view_mode": "graph",
            "domain": [
                ("evaluacion_id", "=", evaluacion_id),
                ("pregunta_id", "=", self.id),
            ],
            "context": {"group_by": "respuesta_texto"},
        }
