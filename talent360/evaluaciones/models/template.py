from odoo import models, fields


class Template(models.Model):
    """
    Modelo para representar una plantilla de evaluación.

    :param _name (str): Nombre del modelo en Odoo.
    :param _description (str): Descripción del modelo en Odoo.
    :param nombre (str): Nombre de la plantilla de evaluación.
    :param tipo (str): Tipo de la plantilla de evaluación, opciones son 'nom_035' para NOM 035 y 'clima' para Clima.
    :param pregunta_ids (fields.Many2many): Relación de muchos a muchos con el modelo 'pregunta' para almacenar las preguntas asociadas a la plantilla.
    """

    _name = "template"
    _description = "Plantilla para una evaluación"
    _rec_name = "nombre"

    nombre = fields.Char(required=True)
    tipo = fields.Selection(
        [
            ("nom_035", "NOM 035"),
            ("clima", "Clima"),
            ("90_grados", "90 grados"),
            ("180_grados", "180 grados"),
        ],
        required=True,
    )

    pregunta_ids = fields.Many2many("pregunta", string="Preguntas")
