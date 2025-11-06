# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    website_menu = fields.Boolean("Menu", help="Allows to display and manage event-specific menus on website.")
