# Copyright (C) 2020, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMTeam(models.Model):
    _inherit = "fsm.team"

    project_id = fields.Many2one("project.project", string="Project")
