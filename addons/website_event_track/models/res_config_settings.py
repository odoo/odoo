# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import event, website


class ResConfigSettings(event.ResConfigSettings, website.ResConfigSettings):

    events_app_name = fields.Char('Events App Name', related='website_id.events_app_name', readonly=False)
