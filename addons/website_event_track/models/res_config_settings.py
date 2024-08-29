# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    events_app_name = fields.Char('Events App Name', related='website_id.events_app_name', readonly=False)
