from odoo import models, fields, api


class Opcion(models.Model):
    """
    Modelo para representar una opción para una pregunta.

    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param pregunta_id (int): Identificador de la pregunta
    :param opcion_texto (str): Texto de la opción
    :param valor (int): Valor de la opción
    """

    _name = "opcion"
    _description = "Opcion para una pregunta"

    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
    opcion_texto = fields.Char("Opción", required=True)
    valor = fields.Integer(required=True, default=0)