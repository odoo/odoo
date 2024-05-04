from odoo import models, fields


class Users(models.Model):
    _name = "res.users"
    _inherit = ["res.users"]

    evaluacion_ids = fields.Many2many(
        "evaluacion",
        "usuario_evaluacion_rel",
        "usuario_id",
        "evaluacion_id",
        string="Evaluaciones",
    )
