from markupsafe import Markup
from ast import literal_eval

from odoo import fields, models, _


class HrJob(models.Model):
    _inherit = "hr.job"

    skill_ids = fields.Many2many(comodel_name='hr.skill', string="Expected Skills")
