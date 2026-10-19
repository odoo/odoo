# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    calendar_show_activities = fields.Boolean(string='Show Activities in Calendar', default=True)
