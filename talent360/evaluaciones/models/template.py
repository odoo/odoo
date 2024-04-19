from odoo import models, fields


class Template(models.Model):
    _name = "template"
    _description = "Plantilla para una evaluación"

    nombre = fields.Char(required=True)
    tipo = fields.Selection(
        [
            ("nom_035", "NOM 035"),
            ("clima", "Clima"),
        ],
        required=True,
    )

    pregunta_ids = fields.Many2many(
        "pregunta",
        "pregunta_template_rel",
        "template_id",
        "pregunta_id",
        string="Preguntas",
    )
