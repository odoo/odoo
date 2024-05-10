from odoo import models, fields


class PreguntaTemplateRel(models.Model):
    """
    Modelo para representar la relación entre plantillas y preguntas
    
    :param _name (str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param template_id (int): Identificador de la plantilla
    :param pregunta_id (int): Identificador de la pregunta
    """
    
    _name = "pregunta.template.rel"
    _description = "Relación entre plantilla y preguntas"

    template_id = fields.Many2one("template", string="Plantilla")
    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
