from odoo import models, fields


class Competencia(models.Model):
    """
    Modelo para almacenar las competencias a evaluar en una evaluación.

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param nombre (str): Nombre de la competencia
    :param descripcion (str): Descripción de la competencia
    :param pregunta_ids (list): Lista de preguntas asociadas a la competencia
    """

    _name = "competencia"
    _description = "Competencia a evaluar"
    _rec_name = "nombre"

    nombre = fields.Char(required=True)
    descripcion = fields.Text("Descripción")

    pregunta_ids = fields.Many2many(
        "pregunta",
        string="Preguntas",
    )
