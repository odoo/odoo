# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import website_event


class WebsiteEventMenu(website_event.WebsiteEventMenu):

    menu_type = fields.Selection(
        selection_add=[('booth', 'Event Booth Menus')], ondelete={'booth': 'cascade'})
