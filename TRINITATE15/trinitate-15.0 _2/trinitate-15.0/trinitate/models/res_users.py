# Copyright 2022 Jarsa
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    editable_messages = fields.Boolean(help="If active, user can edit and delete messages.")
