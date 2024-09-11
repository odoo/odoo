# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarSettings(models.Model):
    _name = "calendar.settings"
    _description = "Settings for calendar connection"

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
