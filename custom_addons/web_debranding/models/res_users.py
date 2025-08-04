# Copyright 2018 Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>
# License MIT (https://opensource.org/licenses/MIT).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    odoobot_state = fields.Selection(string="Bot Status")
