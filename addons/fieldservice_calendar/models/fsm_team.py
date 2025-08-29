# Copyright (C) 2021 Raphaël Reverdy <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMTeam(models.Model):
    _inherit = "fsm.team"

    calendar_user_id = fields.Many2one(
        "res.users",
        string="Team's calendar",
        help="Responsible for orders's calendar",
    )
