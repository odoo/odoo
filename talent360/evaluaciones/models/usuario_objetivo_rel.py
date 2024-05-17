from odoo import models, fields


class UsuarioObjetivoRel(models.Model):
    """
    Modelo para representar la relación entre usuarios y objetivos

    :param _name(str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param evaluacion_id = Identificador de la evaluación
    :param objetivo_id = Identificador del objetivo
    """

    _name = "usuario.objetivo.rel"
    _description = "Relación entre objetivos y usuarios"

    objetivo_id = fields.Many2one("objetivo", string="Objetivos")
    usuario_id = fields.Many2one("res.users", string="Usuario")
