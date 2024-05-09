from odoo import models, fields


class Pregunta(models.Model):
    """
    Modelo para representar una pregunta de una evaluación en Odoo.

    :param ponderacion (fields.Select): Como se ponderan las respuestas.
    """

    _name = "pregunta"
    _inherit = "pregunta"

    # Atributo para definir como se ponderan las respuestas
    # Ejemplo. Ascendente: "Nunca" = 1, "Casi nunca" = 2, "A veces" = 3, "Casi siempre" = 4, "Siempre" = 5
    # Ejemplo. Descendente: "Nunca" = 5, "Casi nunca" = 4, "A veces" = 3, "Casi siempre" = 2, "Siempre" = 1

    ponderacion = fields.Selection(
        [("ascendente", "Ascendente"), ("descendente", "Descendente")],
        string="Ponderación",
        required=False,
    )

    mapeo_valores_escala = {
        "ascendente": {
            "0": "Nunca",
            "1": "Casi nunca",
            "2": "A veces",
            "3": "Casi siempre",
            "4": "Siempre",
        },
        "descendente": {
            "0": "Siempre",
            "1": "Casi siempre",
            "2": "A veces",
            "3": "Casi nunca",
            "4": "Nunca",
        },
    }
