# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventType(models.Model):
    _inherit = "event.type"

    website_meeting_room = fields.Boolean("Website Meeting Room", help="Display community tab on website")
