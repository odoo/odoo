from odoo import models, fields


class Template(models.Model):
    _name = "template"
    _description = "Plantilla para una evaluación"

    nombre = fields.Char(required=True)
    descripcion = fields.Text("Descripción")
    tipo = fields.Selection(
        [
            ("Clima", "Clima"),
            ("nom_085", "NOM 085"),
            ("90_grados", "90 grados"),
            ("180_grados", "180 grados"),
        ],
        default="90_grados",
        required=True,
    )

    pregunta_ids = fields.Many2many("pregunta", string="Preguntas")