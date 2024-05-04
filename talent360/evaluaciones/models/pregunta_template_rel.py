from odoo import models, fields


class PreguntaTemplateRel(models.Model):
    _name = "pregunta.template.rel"
    _description = "Relación entre plantilla y preguntas"

    template_id = fields.Many2one("template", string="Plantilla")
    pregunta_id = fields.Many2one("pregunta", string="Pregunta")
