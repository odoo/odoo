from odoo import models, fields


class UsuarioObjetivoRel(models.Model):
    _name = "usuario.objetivo.rel"
    _description = "Relación entre objetivos y usuarios"

    evaluacion_id = fields.Many2one("objetivo", string="Objetivos")
    usuario_id = fields.Many2one("res.users", string="Usuario")
