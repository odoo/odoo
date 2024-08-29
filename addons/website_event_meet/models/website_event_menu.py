# -*- coding: utf-8 -*-
from odoo.addons import website_event
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteEventMenu(models.Model, website_event.WebsiteEventMenu):

    menu_type = fields.Selection(
        selection_add=[("meeting_room", "Event Meeting Room Menus")],
        ondelete={'meeting_room': 'cascade'})
